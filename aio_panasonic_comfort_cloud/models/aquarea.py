from dataclasses import dataclass
from typing import List, Dict, Any

@dataclass
class AquareaZoneStatus:
    zoneId: int
    zoneName: str
    zoneType: int
    zoneSensor: int
    operationStatus: int
    temperatureNow: int
    heatMin: int
    heatMax: int
    coolMin: int
    coolMax: int
    heatSet: int
    coolSet: int
    ecoHeat: int
    ecoCool: int
    comfortHeat: int
    comfortCool: int

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AquareaZoneStatus":
        return cls(**data)

@dataclass
class AquareaTankStatus:
    operationStatus: int
    temperatureNow: int
    heatMin: int
    heatMax: int
    heatSet: int

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AquareaTankStatus":
        return cls(**data)

@dataclass
class AquareaStatus:
    serviceType: str
    uncontrollableTaw1Flg: bool
    operationMode: int
    coolMode: int
    direction: int
    quietMode: int
    powerful: int
    forceDHW: int
    forceHeater: int
    tank: int
    multiOdConnection: int
    pumpDuty: int
    bivalent: int
    bivalentActual: int
    waterPressure: int
    electricAnode: int
    deiceStatus: int
    specialStatus: int
    outdoorNow: int
    holidayTimer: int
    modelSeriesSelection: int
    standAlone: int
    controlBox: int
    externalHeater: int
    zoneStatus: List[AquareaZoneStatus]
    tankStatus: AquareaTankStatus

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AquareaStatus":
        # Convert the list of dicts into a list of ZoneStatus objects.
        zones_data = data.get('zoneStatus', [])
        zones = [AquareaZoneStatus.from_dict(item) for item in zones_data]
        
        # Convert the tankStatus dict into a TankStatus object.
        tank_data = data.get('tankStatus', {})
        tank_status = AquareaTankStatus.from_dict(tank_data)
        
        # Override the raw data with our converted objects.
        data['zoneStatus'] = zones
        data['tankStatus'] = tank_status
        return cls(**data)

@dataclass
class AquareaStatusResponse:
    operation: str
    ownerFlg: bool
    a2wName: str
    status: AquareaStatus

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AquareaStatusResponse":
        # Convert the nested 'status' dict.
        status_data = data.get('status', {})
        data['status'] = AquareaStatus.from_dict(status_data)
        return cls(**data)
