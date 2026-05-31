import aiohttp
import base64
import hashlib
import logging
import random
import string
import urllib
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
    """Extract a query parameter from a URL string."""
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
        else:
            try:
                code = await self._login(authorization_response, username, password)
            except exceptions.MFARequiredError as e:
                if otp_code is None:
                    raise
                _LOGGER.debug("MFA required and OTP code provided, verifying")
                # Verify the MFA code and get the authorization code
                mfa_result = await self.verify_mfa(otp_code)
                if isinstance(mfa_result, str):
                    code = mfa_result
                else:
                    raise exceptions.ResponseError("MFA verification did not return an authorization code")
        
        await self._request_new_token(code, code_verifier)
        await self._retrieve_client_acc()

    async def verify_mfa(self, otp_code: str):
        """Verify the MFA/2FA OTP code after a login attempt triggered 2FA.

        Args:
            otp_code: The one-time password from the user's authenticator app.

        Returns:
            True if verification succeeded and authentication is complete.

        Raises:
            MFARequiredError: If no pending MFA challenge exists (call authenticate first).
        """
        if not self._mfa_token:
            raise exceptions.MFARequiredError("No pending MFA challenge. Call authenticate() first.")

        # Reset state so a retry is possible
        mfa_token = self._mfa_token
        parameters = dict(self._mfa_parameters)
        self._mfa_token = None
        self._mfa_parameters = {}

        _LOGGER.debug("Submitting MFA verification with OTP code")
        response = await self._client.post(
            f'{BASE_PATH_AUTH}/u2f/mfa/verify',
            headers={
                "Auth0-Client": AUTH_0_CLIENT,
                "user-agent": AUTH_API_USER_AGENT,
            },
            json={
                "mfa_token": mfa_token,
                "mfa_type": "otp",
                "code": otp_code,
                **parameters,
            },
            allow_redirects=False)
        await check_response(response, 'verify_mfa', 200)

        # After successful MFA verification we need to continue the flow
        # The response should redirect us back to the callback
        response_text = await response.text()
        _LOGGER.debug("MFA verification response, %s", json.dumps({'html': response_text}))

        # Parse hidden form fields from the response (similar to login callback)
        soup = BeautifulSoup(response_text, "html.parser")
        input_lines = soup.find_all("input", {"type": "hidden"})
        for input_line in input_lines:
            name = input_line.get("name")
            value = input_line.get("value")
            if name and value is not None:
                self._mfa_parameters[name] = value

        # Check if we got a redirect (MFA verified, proceed to callback)
        if response.status == 200 and 'Location' in response.headers:
            location = response.headers['Location']
            _LOGGER.debug("MFA verification redirect, %s", json.dumps({'redirect': location}))

            # Follow the redirect — this should lead to the final auth code
            follow_response = await self._client.get(
                f"{BASE_PATH_AUTH}/{location}",
                allow_redirects=False)
            await check_response(follow_response, 'mfa_redirect', 302)

            location = follow_response.headers['Location']
            _LOGGER.debug("MFA redirect result, %s", json.dumps({'redirect': location}))

            # Extract the code from the final redirect
            if REDIRECT_URI in location:
                code = get_querystring_parameter_from_url(location, 'code')
                return code
            else:
                # May need another follow
                follow_response2 = await self._client.get(
                    f"{BASE_PATH_AUTH}/{location}",
                    allow_redirects=False)

                if 'Location' in follow_response2.headers:
                    location2 = follow_response2.headers['Location']
                    _LOGGER.debug("MFA second redirect, %s", json.dumps({'redirect': location2}))
                    if REDIRECT_URI in location2:
                        code = get_querystring_parameter_from_url(location2, 'code')
                        return code

        raise exceptions.ResponseError("MFA verification did not produce a valid authorization code")
        
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
            params={
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
            },
            allow_redirects=False)
        await check_response(response, 'authorize', 302)
        return response
        
        
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

        return get_querystring_parameter_from_header_entry_url(
                response, 'Location', 'code')
    
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
            token_response["refresh_token"],
            unix_time_token_received + token_response["expires_in"],
            token_response["scope"])
        
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

