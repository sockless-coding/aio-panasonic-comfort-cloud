import aiohttp
import base64
import hashlib
import logging
import random
import string
import urllib
import urllib.parse
import datetime
import time
import json

from bs4 import BeautifulSoup

from .panasonicsettings import PanasonicSettings
from .ccappversion import CCAppVersion
from .panasonicrequestheader import PanasonicRequestHeader
from . import exceptions
from .constants import (APP_CLIENT_ID, AUTH_0_CLIENT, BASE_PATH_ACC, BASE_PATH_AUTH, REDIRECT_URI, AUTH_API_USER_AGENT, AUTH_BROWSER_USER_AGENT)
from .helpers import has_new_version_been_published, check_response

_LOGGER = logging.getLogger(__name__)

def generate_random_string(length):
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(length))


    
def get_querystring_parameter_from_header_entry_url(response: aiohttp.ClientResponse, header_entry, querystring_parameter):
    header_entry_value = response.headers[header_entry]
    parsed_url = urllib.parse.urlparse(header_entry_value)
    params = urllib.parse.parse_qs(parsed_url.query)
    return params.get(querystring_parameter, [None])[0]


def get_querystring_parameter_from_url(url: str, querystring_parameter: str):
    """Extract a query parameter from a plain URL string."""
    parsed_url = urllib.parse.urlparse(url)
    params = urllib.parse.parse_qs(parsed_url.query)
    return params.get(querystring_parameter, [None])[0]


class PanasonicAuthentication:

    def __init__(self, client: aiohttp.ClientSession, settings: PanasonicSettings, app_version:CCAppVersion):
        self._client = client
        self._settings = settings
        self._app_version = app_version
        # State for 2FA flow
        self._mfa_token = None
        self._mfa_parameters = {}

    async def authenticate(self, username: str, password: str, otp_code: str | None = None):
      
        self._client.cookie_jar.clear_domain('authglb.digital.panasonic.com')
        # Reset 2FA state
        self._mfa_token = None
        self._mfa_parameters = {}

        # generate initial state and code_challenge
        code_verifier = generate_random_string(43)

        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(
                code_verifier.encode('utf-8')
            ).digest()).split('='.encode('utf-8'))[0].decode('utf-8')
        
        authorization_response = await self._authorize(code_challenge)
        authorization_redirect = authorization_response.headers['Location']
        _LOGGER.debug("Authorization result, %s", json.dumps({
            'redirect': authorization_redirect,
            'response': await authorization_response.text()
        }))
        # check if the user can skip the authentication workflows - in that case, 
        # the location is directly pointing to the redirect url with the "code"
        # query parameter included
        if authorization_redirect.startswith(REDIRECT_URI):
            code = get_querystring_parameter_from_header_entry_url(
                authorization_response, 'Location', 'code')
            await self._request_new_token(code, code_verifier)
        else:
            try:
                code = await self._login(authorization_response, username, password)
                await self._request_new_token(code, code_verifier)
            except exceptions.MFARequiredError:
                if otp_code is None:
                    raise
                _LOGGER.debug("MFA required and OTP code provided, verifying")
                # The MFA/OTP exchange below is a token grant, not an
                # authorization code — it sets the token directly rather
                # than going through _request_new_token().
                await self.verify_mfa(otp_code)

        await self._retrieve_client_acc()

    async def verify_mfa(self, otp_code: str):
        """Complete a pending MFA/2FA challenge using Auth0's MFA API.

        This tenant (authglb.digital.panasonic.com) exposes the standard
        Auth0 MFA OOB/OTP API (see its /.well-known/openid-configuration,
        which advertises a "mfa_challenge_endpoint" and the
        "http://auth0.com/oauth/grant-type/mfa-otp" grant type) — unlike the
        rest of the login flow, this part isn't scraped from an HTML page.

        Args:
            otp_code: The one-time password from the user's authenticator app.

        Raises:
            MFARequiredError: If no pending MFA challenge exists (call authenticate first).
        """
        if not self._mfa_token:
            raise exceptions.MFARequiredError("No pending MFA challenge. Call authenticate() first.")

        mfa_token = self._mfa_token
        self._mfa_token = None
        self._mfa_parameters = {}

        # Best-effort challenge negotiation. Auth0 recommends calling this
        # before submitting the code, but plain TOTP/authenticator-app
        # enrollments generally don't require it, so a failure here isn't
        # treated as fatal — we still try the token exchange below.
        try:
            challenge_response = await self._client.post(
                f'{BASE_PATH_AUTH}/mfa/challenge',
                headers={
                    "Auth0-Client": AUTH_0_CLIENT,
                    "user-agent": AUTH_API_USER_AGENT,
                },
                json={
                    "mfa_token": mfa_token,
                    "client_id": APP_CLIENT_ID,
                    "challenge_type": "otp",
                },
                allow_redirects=False)
            _LOGGER.debug("MFA challenge response, %s", json.dumps({
                'status': challenge_response.status,
                'body': await challenge_response.text()
            }))
        except Exception as ex:
            _LOGGER.debug("MFA challenge request failed, continuing with OTP exchange anyway", exc_info=ex)

        now = datetime.datetime.now()
        unix_time_token_received = time.mktime(now.timetuple())

        _LOGGER.debug("Submitting MFA verification with OTP code")
        response = await self._client.post(
            f'{BASE_PATH_AUTH}/oauth/token',
            headers={
                "Auth0-Client": AUTH_0_CLIENT,
                "user-agent": AUTH_API_USER_AGENT,
            },
            json={
                "grant_type": "http://auth0.com/oauth/grant-type/mfa-otp",
                "client_id": APP_CLIENT_ID,
                "mfa_token": mfa_token,
                "otp": otp_code,
            },
            allow_redirects=False)
        await check_response(response, 'verify_mfa', 200)

        token_response = json.loads(await response.text())
        self._set_token(token_response, unix_time_token_received)

    async def refresh_token(self):
        _LOGGER.debug("Refreshing token")
        # do before, so that timestamp is older rather than newer        
        now = datetime.datetime.now()
        unix_time_token_received = time.mktime(now.timetuple())

        response = await self._client.post(
            f'{BASE_PATH_AUTH}/oauth/token',
            headers={
                "Auth0-Client": AUTH_0_CLIENT,
                "user-agent": AUTH_API_USER_AGENT,
            },
            json={
                "scope": self._settings.scope,
                "client_id": APP_CLIENT_ID,
                "refresh_token": self._settings.refresh_token,
                "grant_type": "refresh_token"
            },
            allow_redirects=False)
        await check_response(response, 'refresh_token', 200)
        token_response = json.loads(await response.text())
        self._set_token(token_response, unix_time_token_received)


    @staticmethod
    def _build_authorize_params(challenge: str, state: str) -> dict:
        return {
            "scope": "openid offline_access comfortcloud.control a2w.control",
            "audience": f"https://digital.panasonic.com/{APP_CLIENT_ID}/api/v1/",
            "protocol": "oauth2",
            "response_type": "code",
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "auth0Client": AUTH_0_CLIENT,
            "client_id": APP_CLIENT_ID,
            "redirect_uri": REDIRECT_URI,
            "state": state,
        }

    async def _authorize(self, challenge) -> aiohttp.ClientResponse:
        # --------------------------------------------------------------------
        # AUTHORIZE
        # --------------------------------------------------------------------
        state = generate_random_string(20)
        _LOGGER.debug("Requesting authorization, %s", json.dumps({'challenge': challenge, 'state': state}))

        response = await self._client.get(
            f'{BASE_PATH_AUTH}/authorize',
            headers={
                "user-agent": AUTH_API_USER_AGENT,
            },
            params=self._build_authorize_params(challenge, state),
            allow_redirects=False)
        await check_response(response, 'authorize', 302)
        return response

    # ------------------------------------------------------------------
    # Alternative flow: authenticate in a real browser
    # ------------------------------------------------------------------
    #
    # The rest of this class drives Panasonic's Auth0 "classic" login page
    # itself (POSTing credentials, scraping hidden form fields, following
    # redirects), which is fragile — it has to correctly model whatever
    # Auth0 renders for every possible connection/enrollment (see the MFA
    # bug this was built to fix). These two methods are an alternative that
    # doesn't touch that flow at all: build a standard OAuth2/PKCE
    # authorization URL, have the *caller* open it in an actual browser (a
    # WebView, the system browser, etc.) so Auth0's own hosted page handles
    # login/MFA/social-login natively, then hand the resulting redirect back
    # here to finish the token exchange with the existing, unchanged
    # _request_new_token().

    def build_authorization_url(self) -> tuple[str, str]:
        """Build a URL to open in a real browser to authenticate directly
        with Panasonic's Auth0 tenant, bypassing this library's own
        credential-scraping login flow entirely.

        Returns:
            A ``(authorization_url, code_verifier)`` tuple. Open
            ``authorization_url`` in any browser/WebView; once the user
            finishes logging in (including any MFA/social-login step, all
            handled by Auth0's own page), it will redirect to
            ``panasonic-iot-cfc://authglb.digital.panasonic.com/android/com.panasonic.ACCsmart/callback?code=...``.
            Pass that redirect URL (or just the ``code`` value) together
            with ``code_verifier`` to :meth:`complete_browser_authentication`.
        """
        code_verifier = generate_random_string(43)
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(
                code_verifier.encode('utf-8')
            ).digest()).split('='.encode('utf-8'))[0].decode('utf-8')
        state = generate_random_string(20)
        params = self._build_authorize_params(code_challenge, state)
        authorization_url = f"{BASE_PATH_AUTH}/authorize?{urllib.parse.urlencode(params)}"
        _LOGGER.debug("Built browser authorization URL, %s", json.dumps({'url': authorization_url}))
        return authorization_url, code_verifier

    async def complete_browser_authentication(self, redirect_url_or_code: str, code_verifier: str):
        """Finish authentication started via :meth:`build_authorization_url`.

        Args:
            redirect_url_or_code: Either the full URL the browser was
                redirected to (containing a ``code`` query parameter), or
                just the bare authorization code extracted from it.
            code_verifier: The value returned alongside the authorization
                URL by :meth:`build_authorization_url`.
        """
        code = redirect_url_or_code
        if "://" in redirect_url_or_code or "?" in redirect_url_or_code:
            code = get_querystring_parameter_from_url(redirect_url_or_code, 'code')
            if not code:
                raise exceptions.ResponseError(
                    f"No 'code' parameter found in the provided redirect URL: {redirect_url_or_code}")

        self._client.cookie_jar.clear_domain('authglb.digital.panasonic.com')
        await self._request_new_token(code, code_verifier)
        await self._retrieve_client_acc()
        
        
    async def _login(self, authorization_response: aiohttp.ClientResponse, username, password):
        
        state = get_querystring_parameter_from_header_entry_url(
                authorization_response, 'Location', 'state')
        location = authorization_response.headers['Location']
        _LOGGER.debug("Following authorization redirect, %s", json.dumps({'url': f"{BASE_PATH_AUTH}/{location}", 'state': state}))
        response = await self._client.get(
                f"{BASE_PATH_AUTH}/{location}",
                allow_redirects=False)
        await check_response(response, 'authorize_redirect', 200)
        _LOGGER.debug("Authorization redirect response, %s", json.dumps({ 'headers': dict(response.headers), 'cookies': response.cookies.output() }))

        # get the "_csrf" cookie
        csrf = response.cookies['_csrf']

        # -------------------------------------------------------------------
        # LOGIN
        # -------------------------------------------------------------------
        _LOGGER.debug("Authenticating with username and password, %s", json.dumps({'csrf':csrf,'state':state}))
        response = await self._client.post(
            f'{BASE_PATH_AUTH}/usernamepassword/login',
            headers={
                "Auth0-Client": AUTH_0_CLIENT,
                "user-agent": AUTH_API_USER_AGENT,
            },
            json={
                "client_id": APP_CLIENT_ID,
                "redirect_uri": REDIRECT_URI,
                "tenant": "pdpauthglb-a1",
                "response_type": "code",
                "scope": "openid offline_access comfortcloud.control a2w.control",
                "audience": f"https://digital.panasonic.com/{APP_CLIENT_ID}/api/v1/",
                "_csrf": csrf,
                "state": state,
                "_intstate": "deprecated",
                "username": username,
                "password": password,
                "lang": "en",
                "connection": "PanasonicID-Authentication"
            },
            allow_redirects=False)
        await check_response(response, 'login', 200)

        # -------------------------------------------------------------------
        # CALLBACK
        # -------------------------------------------------------------------

        # get wa, wresult, wctx from body
        response_text = await response.text()
        _LOGGER.debug("Authentication response, %s", json.dumps({'html':response_text}))
        soup = BeautifulSoup(response_text, "html.parser")
        input_lines = soup.find_all("input", {"type": "hidden"})
        parameters = dict()
        for input_line in input_lines:
            parameters[input_line.get("name")] = input_line.get("value")

        # Check if 2FA/MFA is required — Auth0 returns an mfa_token instead of callback params
        mfa_token = parameters.get("mfa_token")
        if mfa_token:
            _LOGGER.debug("MFA/2FA challenge detected, storing mfa_token for verification")
            self._mfa_token = mfa_token
            # Store all other parameters that may be needed for the MFA verify call
            self._mfa_parameters = {k: v for k, v in parameters.items() if k != "mfa_token"}
            raise exceptions.MFARequiredError(mfa_token)

        _LOGGER.debug("Callback with parameters, %s", json.dumps(parameters))
        response = await self._client.post(
            url=f"{BASE_PATH_AUTH}/login/callback",
            data=parameters,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": AUTH_BROWSER_USER_AGENT,
            },
            allow_redirects=False)
        await check_response(response, 'login_callback', 302)

        # ------------------------------------------------------------------
        # FOLLOW REDIRECT
        # ------------------------------------------------------------------

        location = response.headers['Location']
        _LOGGER.debug("Callback response, %s", json.dumps({'redirect':location, 'html': await response.text()}))

        response = await self._client.get(
            f"{BASE_PATH_AUTH}/{location}",
            allow_redirects=False)
        await check_response(response, 'login_redirect', 302)
        location = response.headers['Location']
        _LOGGER.debug("Callback redirect, %s", json.dumps({'redirect':location, 'html': await response.text()}))

        code = get_querystring_parameter_from_header_entry_url(
                response, 'Location', 'code')
        if code:
            return code

        # No authorization code in the final redirect. If we're not already at
        # the app's redirect URI, this is most likely a step-up/MFA challenge
        # that wasn't already caught above (Auth0 only surfaces it here for
        # some connection configurations), so follow it and look for the same
        # hidden mfa_token field before giving up.
        _LOGGER.debug("No 'code' parameter in final redirect, checking for a pending MFA challenge at %s", location)
        if location.startswith(REDIRECT_URI):
            raise exceptions.ResponseError(
                f"Login flow finished at the redirect URI without an authorization code (location: {location})")

        challenge_url = location if location.startswith("http") else f"{BASE_PATH_AUTH}/{location}"
        challenge_response = await self._client.get(challenge_url, allow_redirects=False)
        challenge_text = await challenge_response.text()
        _LOGGER.debug("MFA challenge candidate response, %s", json.dumps({'url': challenge_url, 'html': challenge_text}))

        soup = BeautifulSoup(challenge_text, "html.parser")
        challenge_parameters = {
            input_line.get("name"): input_line.get("value")
            for input_line in soup.find_all("input", {"type": "hidden"})
        }
        mfa_token = challenge_parameters.get("mfa_token")
        if mfa_token:
            _LOGGER.debug("MFA/2FA challenge detected at %s, storing mfa_token for verification", challenge_url)
            self._mfa_token = mfa_token
            self._mfa_parameters = {k: v for k, v in challenge_parameters.items() if k != "mfa_token"}
            raise exceptions.MFARequiredError(mfa_token)

        raise exceptions.ResponseError(
            "Login flow did not produce an authorization code and no MFA challenge could be "
            f"detected (ended at: {challenge_url}). Enable debug logging to inspect the response."
        )

    async def _request_new_token(self, code, code_verifier):
        _LOGGER.debug("Requesting a new token")
        # do before, so that timestamp is older rather than newer
        now = datetime.datetime.now()
        unix_time_token_received = time.mktime(now.timetuple())

        response = await self._client.post(
            f'{BASE_PATH_AUTH}/oauth/token',
            headers={
                "Auth0-Client": AUTH_0_CLIENT,
                "user-agent": AUTH_API_USER_AGENT,
            },
            json={
                "scope": "openid",
                "client_id": APP_CLIENT_ID,
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": REDIRECT_URI,
                "code_verifier": code_verifier
            },
            allow_redirects=False)
        await check_response(response, 'get_token', 200)

        token_response = json.loads(await response.text())
        self._set_token(token_response, unix_time_token_received)
        
    def _set_token(self, token_response, unix_time_token_received):
        self._settings.set_token(
            token_response["access_token"],
            token_response.get("refresh_token"),
            unix_time_token_received + token_response["expires_in"],
            token_response.get("scope"))
        
    async def _retrieve_client_acc(self):
        # ------------------------------------------------------------------
        # RETRIEVE ACC_CLIENT_ID
        # ------------------------------------------------------------------
        _LOGGER.debug("Retrieving acc client id using access token: %s", self._settings.access_token)
      
        response = await self._client.post(
            f'{BASE_PATH_ACC}/auth/v2/login',
            headers = await PanasonicRequestHeader.get(self._settings, self._app_version, include_client_id= False),
            json={
                "language": 0
            })
        if await has_new_version_been_published(response):
            _LOGGER.info("New version of acc client id has been published")
            await self._app_version.refresh()
            response = await self._client.post(
                f'{BASE_PATH_ACC}/auth/v2/login',
                headers = await PanasonicRequestHeader.get(self._settings, self._app_version, include_client_id= False),
                json={
                    "language": 0
                })


        await check_response(response, 'get_acc_client_id', 200)

        json_body = json.loads(await response.text())
        self._settings.clientId = json_body["clientId"]
        return

