import json
import logging
import pytest
from unittest.mock import ANY, MagicMock
from tests.mock_backendselector import BackendSelectorMock

from whirlpool.oven import Oven, Cavity, CavityState, CookMode

from . import MockResponse


pytestmark = pytest.mark.asyncio

ACCOUNT_ID = 111222333
SAID = "WPR1XYZABC123"
AC_NAME = "TestOv"
DATA1 = {
    "_id": SAID,
    "applianceId": SAID,
    "lastFullSyncTime": 1592663948975,
    "lastModified": 1642475181685,
    "attributes": {
        "OvenUpperCavity_DisplaySetUserInstructImageUrl": { "value": "0", "updateTime": 1642158986086 },
        "KitchenTimer01_StatusTimeRemaining": { "value": "0", "updateTime": 1642158986082 },
        "Sys_AlertStatusCustomerFaultCodeNotification": { "value": "0", "updateTime": 1592663948975 },
        "XCat_PowerStatusRealTimePower": { "value": "0", "updateTime": 1642158986079 },
        "XCat_PowerStatusRealTimeCurrent": { "value": "0", "updateTime": 1642158986079 },
        "ISPReasonCode": { "value": "0", "updateTime": 1592663948975 },
        "OvenUpperCavity_DisplaySetOnDemandId": { "value": "1", "updateTime": 1642158986086 },
        "OvenUpperCavity_TimeStatusPreheatTimeRemaining": { "value": "0", "updateTime": 1642158986086 },
        "sys-parser-type": { "value": "0", "updateTime": 1592663948975 },
        "Sys_DisplaySetLanguage": { "value": "0", "updateTime": 1642158986089 },
        "version": { "value": "1", "updateTime": 1642327303387 },
        "XCat_PersistentInfoVersion": { "value": "55", "updateTime": 1642158986079 },
        "SetDNSNames": { "value": "0", "updateTime": 1592663948975 },
        "XCat_SmartGridStatusSmartGridCompliant": { "value": "0", "updateTime": 1642158986079 },
        "ISP_RebootTime": { "value": "1318", "updateTime": 1641282490066 },
        "Relational_ArrayOpen": { "value": "0", "updateTime": 1592663948975 },
        "Relational_to_Appliance": { "value": "0", "updateTime": 1592663948975 },
        "Relational_EnvelopeAction": { "value": "0", "updateTime": 1592663948975 },
        "OvenLowerCavity_OpStatusCleanOven": { "value": "4", "updateTime": 1614730162700 },
        "XCat_OdometerStatusTotalHours": { "value": "13978", "updateTime": 1642472109383 },
        "Sys_DisplaySetBrightnessPercent": { "value": "90", "updateTime": 1642158986089 },
        "ISP_CurrentProcessInModule": { "value": "0", "updateTime": 1641282490066 },
        "XCat_SmartGridSetSmartGridEnable": { "value": "1", "updateTime": 1642158986079 },
        "Relational_EntityId": { "value": "0", "updateTime": 1592663948975 },
        "OvenUpperCavity_DisplaySetUserButton2Time": { "value": "1", "updateTime": 1642158986086 },
        "XCat_PersistentInfoSaid": { "value": SAID, "updateTime": 1642158986079 },
        "uid": { "value": "0", "updateTime": 1592663948975 },
        "PushTrigger": { "value": "0", "updateTime": 1592663948975 },
        "OvenUpperCavity_CycleSetSteamBakeFood": { "value": "0", "updateTime": 1642158986086 },
        "Sys_DisplaySetImage": { "value": "0", "updateTime": 1642158986089 },
        "ConfigTime_SetDelayTimeMax": { "value": "0", "updateTime": 1592663948975 },
        "OvenUpperCavity__RecipeSetFacadeDisplayTemp": { "value": "0", "updateTime": 1642158986086 },
        "Sys_DisplaySetCycleCompleteMessage": { "value": "0", "updateTime": 1592663948975 },
        "Sys_OperationSetControlLock": { "value": "0", "updateTime": 1642158986089 },
        "OvenUpperCavity_DisplaySetCycleCompleteMessage": { "value": "0", "updateTime": 1642158986086 },
        "XCat_WifiStatusIspCheck": { "value": "0", "updateTime": 1642158986079 },
        "OvenLowerCavity_DisplStatusMeatProbeDisplayTemp": { "value": "4", "updateTime": 1615683489232 },
        "OvenUpperCavity_OpStatusState": { "value": "1", "updateTime": 1642475101822 },
        "OvenLowerCavity_DisplStatusDisplayTemp": { "value": "4", "updateTime": 1615683489232 },
        "KitchenTimer01_SetTimeSet": { "value": "0", "updateTime": 1642158986082 },
        "XCat_WifiSetRebootWifiCommModule": { "value": "0", "updateTime": 1642158986079 },
        "XCat_ConfigSetApplianceCapability": { "value": "0", "updateTime": 1592663948975 },
        "ISP_CurrentModule": { "value": "0", "updateTime": 1641282490066 },
        "ConfigCavity_SetTempDefault": { "value": "0", "updateTime": 1592663948975 },
        "XCat_PersistentInfoMacAddress": { "value": "88:e7:12:10:fe:34", "updateTime": 1642158986079 },
        "Sys_OperationSetKeyPressToneVolume": { "value": "4", "updateTime": 1642158986089 },
        "M2MSubList": { "value": "0", "updateTime": 1592663948975 },
        "Relational_EntityClose": { "value": "0", "updateTime": 1592663948975 },
        "ConfigTime_SetCookTimeMax": { "value": "0", "updateTime": 1592663948975 },
        "XCat_OdometerStatusCycleCount": { "value": "557", "updateTime": 1642471899848 },
        "MAC_Address": { "value": "88:e7:12:10:fe:34", "updateTime": 1642327296923 },
        "ISPBundleAttributes": { "value": "0", "updateTime": 1592663948975 },
        "OvenUpperCavity_TimeStatusDelayTimeRemaining": { "value": "0", "updateTime": 1642365862009 },
        "Generic_Zip": { "value": "0", "updateTime": 1592663948975 },
        "OvenLowerCavity_TimeStatusCycleTimeElapsed": { "value": "4", "updateTime": 1613326413669 },
        "Sys_AlertStatusCustomerFaultCode": { "value": "00,00", "updateTime": 1642158986089 },
        "XCat_TimeZoneId": { "value": "0", "updateTime": 1592663948975 },
        "Relational_EnvelopeOpen": {
            "value": "FD010005FE01000304FE02000101050000FE0200034D6F646554696D657300FE02000401FE03000101050001FE02000101050101FE0200034F76656E557070657243617669747900FE03000101050002FE020001010502010310000C02090100010000A8C00901000200000000FE02000201050201FE020001010502020310000C05090100010000A8C00901000200000000FE02000201050202FE020001010502030310000C06090100010000A8C00901000200000000FE02000201050203FE020001010502040310000C08090100010000A8C00901000200000000FE02000201050204FE020001010502050310000C09090100010000A8C00901000200000000FE02000201050205FE020001010502060310000C10090100010000A8C00901000200000000FE02000201050206FE020001010502070310000C18090100010000A8C00901000200000000FE02000201050207FE020001010502080310001002090100010000A8C0090100020000003CFE02000201050208FE020001010502090310001005090100010000A8C0090100020000003CFE02000201050209FE0200010105020A0310001006090100010000A8C0090100020000003CFE0200020105020AFE0200010105020B0310001007090100010000A8C0090100020000003CFE0200020105020BFE0200010105020C0310001008090100010000A8C0090100020000003CFE0200020105020CFE0200010105020D0310001009090100010000A8C0090100020000003CFE0200020105020DFE0200010105020E031000100A090100010000A8C0090100020000003CFE0200020105020EFE0200010105020F031000100B090100010000A8C0090100020000003CFE0200020105020FFE02000101050210031000100C090100010000A8C0090100020000003CFE02000201050210FE02000101050211031000100D090100010000A8C0090100020000003CFE02000201050211FE02000101050212031000100E090100010000A8C0090100020000003CFE02000201050212FE02000101050213031000100F090100010000A8C0090100020000003CFE02000201050213FE020001010502140310001010090100010000A8C0090100020000003CFE02000201050214FE020001010502150310001011090100010000A8C0090100020000003CFE02000201050215FE020001010502160310001012090100010000A8C0090100020000003CFE02000201050216FE020001010502170310001013090100010000A8C0090100020000003CFE02000201050217FE020001010502180310001014090100010000A8C0090100020000003CFE02000201050218FE020001010502190310001015090100010000A8C0090100020000003CFE02000201050219FE0200010105021A0310001016090100010000A8C0090100020000003CFE0200020105021AFE0200010105021B03100012020901000100002A3009010002000004B0FE0200020105021BFE0200010105021C03100012030901000100000E100901000200000258FE0200020105021CFE0200010105021D03100012040901000100002A3009010002000004B0FE0200020105021DFE0200010105021E0310001205090100010000A8C00901000200000258FE0200020105021EFE0200010105021F03100012060901000100002A300901000200000258FE0200020105021FFE0200010105021F03100012070901000100002A300901000200000258FE02000201050220FE03000201050002FE02000201050101FE03000201050001FE02000201050000FE010002FD010005",
            "updateTime": 1622434893963
        },
        "OvenUpperCavity_DisplaySetEmbeddedUserInstructId": { "value": "0", "updateTime": 1642158986086 },
        "Relational_CapabilityTimeDefaults": { "value": "0", "updateTime": 1592663948975 },
        "XCat_WifiSetDeprovisionWifiCommModule": { "value": "0", "updateTime": 1642158986079 },
        "OvenUpperCavity_CycleSetConvectSlowRoastTime": { "value": "0", "updateTime": 1642158986086 },
        "GetSubscribeListVersion": { "value": "0", "updateTime": 1592663948975 },
        "OvenUpperCavity_CycleSetMeatProbeTargetTemp": { "value": "0", "updateTime": 1642475100333 },
        "Sys_AlertStatusNotification": { "value": "0", "updateTime": 1642360716508 },
        "ConfigKitchenTimer_SetMin": { "value": "0", "updateTime": 1592663948975 },
        "SysHeader_RecipeSetRecipeSummary": { "value": "0", "updateTime": 1642158986089 },
        "XCat_OdometerStatusRunningHours": { "value": "39", "updateTime": 1642158986079 },
        "XCat_DateTimeSetDateFormat": { "value": "0", "updateTime": 1642158986079 },
        "ccuri": { "value": "API144_COOKING_V55", "updateTime": 1642327296923 },
        "SerialNumber": { "value": "xxxxxxxxx", "updateTime": 1642327296923 },
        "OvenUpperCavity_DisplaySetCookingImageUrI": { "value": "00,00", "updateTime": 1642158986086 },
        "XCat_UtcOffset": { "value": "0", "updateTime": 1592663948975 },
        "XCat_WifiSetDisableWifiCommModule": { "value": "0", "updateTime": 1642158986079 },
        "KitchenTimer01_SetOperations": { "value": "0", "updateTime": 1642158986082 },
        "ConfigCavity_SetTempMin": { "value": "0", "updateTime": 1592663948975 },
        "OvenUpperCavity_DisplaySetZonedMessage": { "value": "0", "updateTime": 1642158986086 },
        "Sys_OperationSetConvertTemp": { "value": "0", "updateTime": 1592663948975 },
        "XCat_ConfigSetMaxRelationalMemory": { "value": "0", "updateTime": 1592663948975 },
        "XCat_DateTimeMode": { "value": "0", "updateTime": 1592663948975 },
        "Sys_AlertStatusRemoteDiagnosticsResults": { "value": "0", "updateTime": 1592663948975 },
        "OvenUpperCavity_CycleSetMode": { "value": "0", "updateTime": 1598197656208 },
        "Sys_DisplaySetTempUnits": { "value": "1", "updateTime": 1642158986089 },
        "XCat_SmartGridSetSmartGridMode": { "value": "0,0,0,0,0", "updateTime": 1642158986079 },
        "Cooktop_OperationStatusState": { "value": "4", "updateTime": 1615764644034 },
        "OvenUpperCavity_AlertSetUserInstructToneSelect": { "value": "1", "updateTime": 1642158986086 },
        "XCat_PowerSetRealTimePowerPublishTiming": { "value": "0", "updateTime": 1642158986079 },
        "OvenUpperCavity_OpStatusDoorLocked": { "value": "0", "updateTime": 1642158986086 },
        "CC_URI": { "value": "API144_COOKING_V22", "updateTime": 1595805342488 },
        "XCat_InServiceDate": { "value": "0", "updateTime": 1592663948975 },
        "KitchenTimer01_StatusState": { "value": "0", "updateTime": 1642158986082 },
        "OvenUpperCavity_TimeStatusCycleTimeElapsed": { "value": "81", "updateTime": 1642475181488 },
        "OvenUpperCavity_CulinaryCtrSetQuantity": { "value": "0", "updateTime": 1642158986086 },
        "OvenUpperCavity_AlertSetToneSelect": { "value": "1", "updateTime": 1642158986086 },
        "SysHeader_RecipeSetRecipeId": { "value": "0", "updateTime": 1642158986089 },
        "ISP_REASON_CODE": { "value": "0", "updateTime": 1641282489979 },
        "OvenUpperCavity_CycleSetBrowning": { "value": "0", "updateTime": 1642158986086 },
        "OvenUpperCavity_DisplaySetEmbUsrInsCmpltAction": { "value": "128", "updateTime": 1642158986086 },
        "Sys_OperationSetQuietModeEnabled": { "value": "0", "updateTime": 1642158986089 },
        "M2MSubscribeListVersion": { "value": "0", "updateTime": 1592663948975 },
        "SubscribeClaimstate": { "value": "1", "updateTime": 1595477123054 },
        "OvenLowerCavity_OpStatusState": { "value": "4", "updateTime": 1614745152496 },
        "OvenUpperCavity_CycleSetSousVide": { "value": "0", "updateTime": 1642158986086 },
        "OvenUpperCavity_CycleSetExtraCookingTime": { "value": "0", "updateTime": 1642158986086 },
        "OvenUpperCavity_CycleSetCommonMode": { "value": "2", "updateTime": 1642475100329 },
        "TimeZoneId": { "value": "America/Los_Angeles", "updateTime": 1642327303390 },
        "OvenLowerCavity_OpStatusDoorOpen": { "value": "4", "updateTime": 1596933673209 },
        "Relational_EntityOpen": { "value": "0", "updateTime": 1592663948975 },
        "GetApplianceVersionNumber": { "value": "0", "updateTime": 1592663948975 },
        "OvenUpperCavity_DisplaySetUserButton1Time": { "value": "1", "updateTime": 1642158986086 },
        "XCat_ApplianceInfoSetSerialNumber": { "value": "xxxxxxxxx", "updateTime": 1642158986079 },
        "OvenUpperCavity_CycleSetDonenessAdjust": { "value": "0", "updateTime": 1642158986086 },
        "Relational_CapabilityModeTemperatures": { "value": "0", "updateTime": 1592663948975 },
        "XCat_PowerStatusEnergyMeasurementResults": { "value": "0", "updateTime": 1642158986079 },
        "Sys_DisplaySetZonedMessage": { "value": "0", "updateTime": 1592663948975 },
        "OvenUpperCavity_DisplaySetLightOn": { "value": "0", "updateTime": 1642443644576 },
        "XCat_DstOffset": { "value": "0", "updateTime": 1592663948975 },
        "Generic_UtilityID": { "value": "0", "updateTime": 1592663948975 },
        "OvenUpperCavity_CycleSetPreheatOn": { "value": "0", "updateTime": 1642158986086 },
        "Generic_SmartID": { "value": "0", "updateTime": 1592663948975 },
        "OvenUpperCavity_CycleSetCleanOvenMode": { "value": "0", "updateTime": 1642158986086 },
        "Relational_CapabilitySettings": { "value": "0", "updateTime": 1592663948975 },
        "ISP_PART_NUMBER": { "value": "W11569991", "updateTime": 1642327302255 },
        "OvenUpperCavity_CycleSetFrozenBakeFood": { "value": "0", "updateTime": 1642437699882 },
        "ConfigTime_SetDelayTimeMin": { "value": "0", "updateTime": 1592663948975 },
        "OvenUpperCavity_DisplaySetUserButton2Action": { "value": "0", "updateTime": 1642158986086 },
        "Generic_EnergyProfileSetting": { "value": "0", "updateTime": 1592663948975 },
        "ISP_DownloadEnd": { "value": "0", "updateTime": 1641282490066 },
        "SysHeader_RecipeSetRecipeTime": { "value": "0", "updateTime": 1642158986089 },
        "ISP_UpdateNotification": { "value": "1641252363", "updateTime": 1641282490066 },
        "OvenUpperCavity_CycleSetCommonModeProbe": { "value": "0", "updateTime": 1642158986086 },
        "OvenUpperCavity_TimeSetDelayTime": { "value": "0", "updateTime": 1642471899830 },
        "OvenUpperCavity_OpStatusCleanOven": { "value": "0", "updateTime": 1642158986086 },
        "OvenUpperCavity_CycleSetEasySteamFood": { "value": "0", "updateTime": 1642158986086 },
        "OvenUpperCavity_CycleSetBreadProof": { "value": "0", "updateTime": 1642158986086 },
        "Relational_EntityName": { "value": "0", "updateTime": 1592663948975 },
        "ISP_InstallEnd": { "value": "0", "updateTime": 1641282490066 },
        "ISP_TotalProcessInModule": { "value": "0", "updateTime": 1641282490066 },
        "OvenUpperCavity_DisplaySetMessage": { "value": "0", "updateTime": 1592663948975 },
        "OvenUpperCavity_AlertStatusMeatProbePluggedIn": { "value": "0", "updateTime": 1642158986086 },
        "TimezoneId": { "value": "America/Phoenix", "updateTime": 1595865616981 },
        "Sys_DisplayStatusBroilDisplayType": { "value": "2", "updateTime": 1642158986089 },
        "XCat_trid": { "value": "0", "updateTime": 1592663948975 },
        "orgId": { "value": "NAR", "updateTime": 1595805342488 },
        "XCat_RemoteSetRemoteControlEnable": { "value": "1", "updateTime": 1642158986079 },
        "UtcOffset": { "value": "-25200", "updateTime": 1595865616981 },
        "ConfigUint8Range_SetMin": { "value": "0", "updateTime": 1592663948975 },
        "OvenUpperCavity_CustomCycleSetId": { "value": "0", "updateTime": 1642158986086 },
        "OvenUpperCavity_CycleSetSteamPercent": { "value": "0", "updateTime": 1642158986086 },
        "OvenUpperCavity_CulinaryCtrSetId": { "value": "0", "updateTime": 1642158986086 },
        "XCat_ConfigSetMaxRelationalSteps": { "value": "0", "updateTime": 1592663948975 },
        "XCat_RemoteSetRebootAppliance": { "value": "0", "updateTime": 1642158986079 },
        "XCat_trid_result": { "value": "0", "updateTime": 1592663948975 },
        "OvenUpperCavity_CycleSetDoneness": { "value": "0", "updateTime": 1642158986086 },
        "ConfigTime_SetCookTimeMin": { "value": "0", "updateTime": 1592663948975 },
        "OvenLowerCavity_AlertStatusMeatProbePluggedIn": { "value": "4", "updateTime": 1612655437184 },
        "Sys_DisplaySetCompleteActionTimeout": { "value": "120", "updateTime": 1642158986089 },
        "Relational_CapabilityModeTimes": { "value": "0", "updateTime": 1592663948975 },
        "Generic_RatePlanID": { "value": "0", "updateTime": 1592663948975 },
        "Sys_OperationSetGreaseFilter": { "value": "0", "updateTime": 1642158986089 },
        "XCat_PowerStatusEnergyConsumption": { "value": "0", "updateTime": 1642471899841 },
        "XCat_DateTimeSetDateTimeSet": { "value": "2022-01-14T03:16:24+00:00", "updateTime": 1642158986079 },
        "OvenUpperCavity_TimeSetCookTimeSet": { "value": "0", "updateTime": 1642471899819 },
        "OvenUpperCavity_CycleSetEasyConvectFood": { "value": "0", "updateTime": 1642471899822 },
        "Relational_EnvelopeClose": { "value": "0", "updateTime": 1592663948975 },
        "Online": { "value": "1", "updateTime": 1642327293148 },
        "XCat_PowerSetRealTimePowerPublishStart": { "value": "0", "updateTime": 1642158986079 },
        "OvenUpperCavity_CycleSetMultiRackFood": { "value": "0", "updateTime": 1642158986086 },
        "Relational_ArrayClose": { "value": "0", "updateTime": 1592663948975 },
        "Sys_OperationSetSabbathModeEnabled": { "value": "0", "updateTime": 1642158986089 },
        "OvenUpperCavity__RecipeSetFacadeCookTime": { "value": "0", "updateTime": 1642158986086 },
        "Sys_OperationSetAlertToneVolume": { "value": "4", "updateTime": 1642158986089 },
        "body": {
            "value": "{node=3, nameSpaceID=255, Online=1, uri=API147_INDIGO_MGT_INDIGO_V1}",
            "updateTime": 1595718364528
        },
        "Sys_DisplaySetMessage": { "value": "0", "updateTime": 1592663948975 },
        "OvenUpperCavity_TimeSetCookTimeOperations": { "value": "0", "updateTime": 1642471899811 },
        "OvenUpperCavity_CycleSetConvectBakeFood": { "value": "0", "updateTime": 1642158986086 },
        "OvenUpperCavity_DisplaySetUserButton1Action": { "value": "0", "updateTime": 1642158986086 },
        "ConfigUint8Range_SetStep": { "value": "0", "updateTime": 1592663948975 },
        "OvenUpperCavity_CycleStatusOdometer": { "value": "555", "updateTime": 1642471901316 },
        "ModelNumber": { "value": "WOS72EC0HS01", "updateTime": 1642327296923 },
        "OvenUpperCavity_CycleSetFrozenCustomFood": { "value": "0", "updateTime": 1642158986086 },
        "ProjectReleaseNumber": { "value": "0", "updateTime": 1592663948975 },
        "ApplianceVersionNumber": { "value": "20", "updateTime": 1642327302255 },
        "OvenUpperCavity_CycleSetSlowCookingFood": { "value": "0", "updateTime": 1642158986086 },
        "ConfigCavity_SetTempMax": { "value": "0", "updateTime": 1592663948975 },
        "ConfigKitchenTimer_SetMax": { "value": "0", "updateTime": 1592663948975 },
        "OvenUpperCavity_DisplStatusMeatProbeDisplayTemp": { "value": "0", "updateTime": 1642158986086 },
        "XCat_RemoteSetRemoteDiagnosticsEnable": { "value": "0", "updateTime": 1642158986079 },
        "XCat_PowerStatusRealTimeVoltage": { "value": "0", "updateTime": 1642158986079 },
        "OvenLowerCavity_OpStatusCookTimeState": { "value": "4", "updateTime": 1614744414817 },
        "Sys_OperationSetConvertTime": { "value": "0", "updateTime": 1592663948975 },
        "XCat_WifiStatusRssiAntennaDiversity": { "value": "-61", "updateTime": 1642158986079 },
        "OvenUpperCavity_OpSetOperations": { "value": "2", "updateTime": 1642475100321 },
        "header": { "value": "{SAID=xxxxxxxxx}", "updateTime": 1595718364528 },
        "Sys_AlertStatusControlLockChangedByAppliance": { "value": "0", "updateTime": 1592663948975 },
        "XCat_PowerStatusPowerOutage": { "value": "0", "updateTime": 1642158986079 },
        "OvenUpperCavity_OpStatusCookTimeState": { "value": "0", "updateTime": 1642471901371 },
        "ConfigUint8Range_SetMax": { "value": "0", "updateTime": 1592663948975 },
        "OvenUpperCavity_DisplaySetUserButton3Action": { "value": "0", "updateTime": 1642158986086 },
        "OvenUpperCavity_CycleSetTargetTemp": { "value": "1766", "updateTime": 1642475100336 },
        "XCat_PowerSetEnergyMeasurementStart": { "value": "0", "updateTime": 1642158986079 },
        "OvenUpperCavity_DisplStatusDisplayTemp": { "value": "377", "updateTime": 1642475100343 },
        "OvenUpperCavity__RecipeSetFacadeMode": { "value": "0", "updateTime": 1642158986086 },
        "XCat_WifiSetPublishApplianceState": { "value": "0", "updateTime": 1642158986079 },
        "OvenLowerCavity_CycleStatusOdometer": { "value": "54", "updateTime": 1598492874556 },
        "Sys_DisplaySetEnable24Hour": { "value": "0", "updateTime": 1642158986089 },
        "SAID": { "value": SAID, "updateTime": 1642327296923 },
        "XCat_WifiSetIspFirmwareDescriptionUrl": { "value": "0", "updateTime": 1592663948975 },
        "Relational_CycleMyCreation": { "value": "0", "updateTime": 1592663948975 },
        "OvenUpperCavity_OpSetMachineInstructCmpltAction": { "value": "0", "updateTime": 1642158986086 },
        "DstOffset": { "value": "0", "updateTime": 1595865616981 },
        "OvenUpperCavity_DisplaySetUserButton3Time": { "value": "1", "updateTime": 1642158986086 },
        "XCat_ApplianceInfoSetModelNumber": { "value": "WOS72EC0HS01", "updateTime": 1642158986079 },
        "DateTimeMode": { "value": "2", "updateTime": 1595865616981 },
        "XCat_WifiSetIspAuthorized": { "value": "0", "updateTime": 1642158986079 },
        "OvenUpperCavity_OpSetSabbathModeActive": { "value": "0", "updateTime": 1642158986086 },
        "OvenUpperCavity_TimeStatusCookTimeRemaining": { "value": "0", "updateTime": 1642471907353 },
        "OvenUpperCavity_CustomCycleSetStep": { "value": "0", "updateTime": 1642158986086 },
        "ConfigDisplay_SetZoneMessageLength": { "value": "0", "updateTime": 1592663948975 },
        "Sys_OperationSetCharcoalFilter": { "value": "0", "updateTime": 1642158986089 },
        "OvenLowerCavity_OpStatusDoorLocked": { "value": "4", "updateTime": 1613006545397 },
        "ISP_WIFI_VERSION": { "value": "1.cb.0", "updateTime": 1642327302255 },
        "OvenUpperCavity_OpStatusDoorOpen": { "value": "0", "updateTime": 1642360848734 },
        "Mwo_CycleStatusOdometer": { "value": "54", "updateTime": 1598492874562 },
        "ISP_DownloadStart": { "value": "0", "updateTime": 1641282490066 },
        "ISP_WIFI_PART_NUMBER": { "value": "W10835199", "updateTime": 1642327302255 },
        "OvenUpperCavity_OpSetCookTimeCompleteAction": { "value": "3", "updateTime": 1642475100325 },
        "OvenUpperCavity_CycleStatusMyCreationsId": { "value": "0", "updateTime": 1592875509959 },
        "ConfigKitchenTimer_SetSelect": { "value": "0", "updateTime": 1592663948975 },
        "ISP_InstallStart": { "value": "0", "updateTime": 1641282490066 },
        "OvenUpperCavity_CycleSetEasyProbe": { "value": "0", "updateTime": 1642158986086 }
    },
}
DATA2 = {
    "_id": SAID,
    "applianceId": SAID,
    "lastFullSyncTime": 1604500393149,
    "lastModified": 1642158986086,
    "attributes": {
        "OvenUpperCavity_DisplaySetUserInstructImageUrl": { "value": "0", "updateTime": 1642158986086 },
        "KitchenTimer01_StatusTimeRemaining": { "value": "0", "updateTime": 1642158986082 },
        "Sys_AlertStatusCustomerFaultCodeNotification": { "value": "0", "updateTime": 1592663948975 },
        "XCat_PowerStatusRealTimePower": { "value": "0", "updateTime": 1642158986079 },
        "XCat_PowerStatusRealTimeCurrent": { "value": "0", "updateTime": 1642158986079 },
        "ISPReasonCode": { "value": "0", "updateTime": 1592663948975 },
        "OvenUpperCavity_DisplaySetOnDemandId": { "value": "1", "updateTime": 1642158986086 },
        "OvenUpperCavity_TimeStatusPreheatTimeRemaining": { "value": "0", "updateTime": 1642158986086 },
        "sys-parser-type": { "value": "0", "updateTime": 1592663948975 },
        "Sys_DisplaySetLanguage": { "value": "0", "updateTime": 1642158986089 },
        "version": { "value": "1", "updateTime": 1642327303387 },
        "XCat_PersistentInfoVersion": { "value": "55", "updateTime": 1642158986079 },
        "SetDNSNames": { "value": "0", "updateTime": 1592663948975 },
        "XCat_SmartGridStatusSmartGridCompliant": { "value": "0", "updateTime": 1642158986079 },
        "ISP_RebootTime": { "value": "1318", "updateTime": 1641282490066 },
        "Relational_ArrayOpen": { "value": "0", "updateTime": 1592663948975 },
        "Relational_to_Appliance": { "value": "0", "updateTime": 1592663948975 },
        "Relational_EnvelopeAction": { "value": "0", "updateTime": 1592663948975 },
        "OvenLowerCavity_OpStatusCleanOven": { "value": "4", "updateTime": 1614730162700 },
        "XCat_OdometerStatusTotalHours": { "value": "13973", "updateTime": 1642454108661 },
        "Sys_DisplaySetBrightnessPercent": { "value": "70", "updateTime": 1642158986089 },
        "ISP_CurrentProcessInModule": { "value": "0", "updateTime": 1641282490066 },
        "XCat_SmartGridSetSmartGridEnable": { "value": "1", "updateTime": 1642158986079 },
        "Relational_EntityId": { "value": "0", "updateTime": 1592663948975 },
        "OvenUpperCavity_DisplaySetUserButton2Time": { "value": "1", "updateTime": 1642158986086 },
        "XCat_PersistentInfoSaid": { "value": SAID, "updateTime": 1642158986079 },
        "uid": { "value": "0", "updateTime": 1592663948975 },
        "PushTrigger": { "value": "0", "updateTime": 1592663948975 },
        "OvenUpperCavity_CycleSetSteamBakeFood": { "value": "0", "updateTime": 1642158986086 },
        "Sys_DisplaySetImage": { "value": "0", "updateTime": 1642158986089 },
        "ConfigTime_SetDelayTimeMax": { "value": "0", "updateTime": 1592663948975 },
        "OvenUpperCavity__RecipeSetFacadeDisplayTemp": { "value": "0", "updateTime": 1642158986086 },
        "Sys_DisplaySetCycleCompleteMessage": { "value": "0", "updateTime": 1592663948975 },
        "Sys_OperationSetControlLock": { "value": "1", "updateTime": 1642158986089 },
        "OvenUpperCavity_DisplaySetCycleCompleteMessage": { "value": "0", "updateTime": 1642158986086 },
        "XCat_WifiStatusIspCheck": { "value": "0", "updateTime": 1642158986079 },
        "OvenLowerCavity_DisplStatusMeatProbeDisplayTemp": { "value": "4", "updateTime": 1615683489232 },
        "OvenUpperCavity_OpStatusState": { "value": "0", "updateTime": 1642443644570 },
        "OvenLowerCavity_DisplStatusDisplayTemp": { "value": "4", "updateTime": 1615683489232 },
        "KitchenTimer01_SetTimeSet": { "value": "0", "updateTime": 1642158986082 },
        "XCat_WifiSetRebootWifiCommModule": { "value": "0", "updateTime": 1642158986079 },
        "XCat_ConfigSetApplianceCapability": { "value": "0", "updateTime": 1592663948975 },
        "ISP_CurrentModule": { "value": "0", "updateTime": 1641282490066 },
        "ConfigCavity_SetTempDefault": { "value": "0", "updateTime": 1592663948975 },
        "XCat_PersistentInfoMacAddress": { "value": "88:e7:12:10:fe:34", "updateTime": 1642158986079 },
        "Sys_OperationSetKeyPressToneVolume": { "value": "4", "updateTime": 1642158986089 },
        "M2MSubList": { "value": "0", "updateTime": 1592663948975 },
        "Relational_EntityClose": { "value": "0", "updateTime": 1592663948975 },
        "ConfigTime_SetCookTimeMax": { "value": "0", "updateTime": 1592663948975 },
        "XCat_OdometerStatusCycleCount": { "value": "556", "updateTime": 1642443644560 },
        "MAC_Address": { "value": "88:e7:12:10:fe:34", "updateTime": 1642327296923 },
        "ISPBundleAttributes": { "value": "0", "updateTime": 1592663948975 },
        "OvenUpperCavity_TimeStatusDelayTimeRemaining": { "value": "0", "updateTime": 1642365862009 },
        "Generic_Zip": { "value": "0", "updateTime": 1592663948975 },
        "OvenLowerCavity_TimeStatusCycleTimeElapsed": { "value": "4", "updateTime": 1613326413669 },
        "Sys_AlertStatusCustomerFaultCode": { "value": "00,00", "updateTime": 1642158986089 },
        "XCat_TimeZoneId": { "value": "0", "updateTime": 1592663948975 },
        "Relational_EnvelopeOpen": {
            "value": "FD010005FE01000304FE02000101050000FE0200034D6F646554696D657300FE02000401FE03000101050001FE02000101050101FE0200034F76656E557070657243617669747900FE03000101050002FE020001010502010310000C02090100010000A8C00901000200000000FE02000201050201FE020001010502020310000C05090100010000A8C00901000200000000FE02000201050202FE020001010502030310000C06090100010000A8C00901000200000000FE02000201050203FE020001010502040310000C08090100010000A8C00901000200000000FE02000201050204FE020001010502050310000C09090100010000A8C00901000200000000FE02000201050205FE020001010502060310000C10090100010000A8C00901000200000000FE02000201050206FE020001010502070310000C18090100010000A8C00901000200000000FE02000201050207FE020001010502080310001002090100010000A8C0090100020000003CFE02000201050208FE020001010502090310001005090100010000A8C0090100020000003CFE02000201050209FE0200010105020A0310001006090100010000A8C0090100020000003CFE0200020105020AFE0200010105020B0310001007090100010000A8C0090100020000003CFE0200020105020BFE0200010105020C0310001008090100010000A8C0090100020000003CFE0200020105020CFE0200010105020D0310001009090100010000A8C0090100020000003CFE0200020105020DFE0200010105020E031000100A090100010000A8C0090100020000003CFE0200020105020EFE0200010105020F031000100B090100010000A8C0090100020000003CFE0200020105020FFE02000101050210031000100C090100010000A8C0090100020000003CFE02000201050210FE02000101050211031000100D090100010000A8C0090100020000003CFE02000201050211FE02000101050212031000100E090100010000A8C0090100020000003CFE02000201050212FE02000101050213031000100F090100010000A8C0090100020000003CFE02000201050213FE020001010502140310001010090100010000A8C0090100020000003CFE02000201050214FE020001010502150310001011090100010000A8C0090100020000003CFE02000201050215FE020001010502160310001012090100010000A8C0090100020000003CFE02000201050216FE020001010502170310001013090100010000A8C0090100020000003CFE02000201050217FE020001010502180310001014090100010000A8C0090100020000003CFE02000201050218FE020001010502190310001015090100010000A8C0090100020000003CFE02000201050219FE0200010105021A0310001016090100010000A8C0090100020000003CFE0200020105021AFE0200010105021B03100012020901000100002A3009010002000004B0FE0200020105021BFE0200010105021C03100012030901000100000E100901000200000258FE0200020105021CFE0200010105021D03100012040901000100002A3009010002000004B0FE0200020105021DFE0200010105021E0310001205090100010000A8C00901000200000258FE0200020105021EFE0200010105021F03100012060901000100002A300901000200000258FE0200020105021FFE0200010105021F03100012070901000100002A300901000200000258FE02000201050220FE03000201050002FE02000201050101FE03000201050001FE02000201050000FE010002FD010005",
            "updateTime": 1622434893963
        },
        "OvenUpperCavity_DisplaySetEmbeddedUserInstructId": { "value": "0", "updateTime": 1642158986086 },
        "Relational_CapabilityTimeDefaults": { "value": "0", "updateTime": 1592663948975 },
        "XCat_WifiSetDeprovisionWifiCommModule": { "value": "0", "updateTime": 1642158986079 },
        "OvenUpperCavity_CycleSetConvectSlowRoastTime": { "value": "0", "updateTime": 1642158986086 },
        "GetSubscribeListVersion": { "value": "0", "updateTime": 1592663948975 },
        "OvenUpperCavity_CycleSetMeatProbeTargetTemp": { "value": "0", "updateTime": 1642443644552 },
        "Sys_AlertStatusNotification": { "value": "0", "updateTime": 1642360716508 },
        "ConfigKitchenTimer_SetMin": { "value": "0", "updateTime": 1592663948975 },
        "SysHeader_RecipeSetRecipeSummary": { "value": "0", "updateTime": 1642158986089 },
        "XCat_OdometerStatusRunningHours": { "value": "39", "updateTime": 1642158986079 },
        "XCat_DateTimeSetDateFormat": { "value": "0", "updateTime": 1642158986079 },
        "ccuri": { "value": "API144_COOKING_V55", "updateTime": 1642327296923 },
        "SerialNumber": { "value": "xxxxxxxxx", "updateTime": 1642327296923 },
        "OvenUpperCavity_DisplaySetCookingImageUrI": { "value": "00,00", "updateTime": 1642158986086 },
        "XCat_UtcOffset": { "value": "0", "updateTime": 1592663948975 },
        "XCat_WifiSetDisableWifiCommModule": { "value": "0", "updateTime": 1642158986079 },
        "KitchenTimer01_SetOperations": { "value": "0", "updateTime": 1642158986082 },
        "ConfigCavity_SetTempMin": { "value": "0", "updateTime": 1592663948975 },
        "OvenUpperCavity_DisplaySetZonedMessage": { "value": "0", "updateTime": 1642158986086 },
        "Sys_OperationSetConvertTemp": { "value": "0", "updateTime": 1592663948975 },
        "XCat_ConfigSetMaxRelationalMemory": { "value": "0", "updateTime": 1592663948975 },
        "XCat_DateTimeMode": { "value": "0", "updateTime": 1592663948975 },
        "Sys_AlertStatusRemoteDiagnosticsResults": { "value": "0", "updateTime": 1592663948975 },
        "OvenUpperCavity_CycleSetMode": { "value": "0", "updateTime": 1598197656208 },
        "Sys_DisplaySetTempUnits": { "value": "1", "updateTime": 1642158986089 },
        "XCat_SmartGridSetSmartGridMode": { "value": "0,0,0,0,0", "updateTime": 1642158986079 },
        "Cooktop_OperationStatusState": { "value": "4", "updateTime": 1615764644034 },
        "OvenUpperCavity_AlertSetUserInstructToneSelect": { "value": "1", "updateTime": 1642158986086 },
        "XCat_PowerSetRealTimePowerPublishTiming": { "value": "0", "updateTime": 1642158986079 },
        "OvenUpperCavity_OpStatusDoorLocked": { "value": "0", "updateTime": 1642158986086 },
        "CC_URI": { "value": "API144_COOKING_V22", "updateTime": 1595805342488 },
        "XCat_InServiceDate": { "value": "0", "updateTime": 1592663948975 },
        "KitchenTimer01_StatusState": { "value": "0", "updateTime": 1642158986082 },
        "OvenUpperCavity_TimeStatusCycleTimeElapsed": { "value": "0", "updateTime": 1642443652036 },
        "OvenUpperCavity_CulinaryCtrSetQuantity": { "value": "0", "updateTime": 1642158986086 },
        "OvenUpperCavity_AlertSetToneSelect": { "value": "1", "updateTime": 1642158986086 },
        "SysHeader_RecipeSetRecipeId": { "value": "0", "updateTime": 1642158986089 },
        "ISP_REASON_CODE": { "value": "0", "updateTime": 1641282489979 },
        "OvenUpperCavity_CycleSetBrowning": { "value": "0", "updateTime": 1642158986086 },
        "OvenUpperCavity_DisplaySetEmbUsrInsCmpltAction": { "value": "128", "updateTime": 1642158986086 },
        "Sys_OperationSetQuietModeEnabled": { "value": "0", "updateTime": 1642158986089 },
        "M2MSubscribeListVersion": { "value": "0", "updateTime": 1592663948975 },
        "SubscribeClaimstate": { "value": "1", "updateTime": 1595477123054 },
        "OvenLowerCavity_OpStatusState": { "value": "4", "updateTime": 1614745152496 },
        "OvenUpperCavity_CycleSetSousVide": { "value": "0", "updateTime": 1642158986086 },
        "OvenUpperCavity_CycleSetExtraCookingTime": { "value": "0", "updateTime": 1642158986086 },
        "OvenUpperCavity_CycleSetCommonMode": { "value": "0", "updateTime": 1642443644519 },
        "TimeZoneId": { "value": "America/Los_Angeles", "updateTime": 1642327303390 },
        "OvenLowerCavity_OpStatusDoorOpen": { "value": "4", "updateTime": 1596933673209 },
        "Relational_EntityOpen": { "value": "0", "updateTime": 1592663948975 },
        "GetApplianceVersionNumber": { "value": "0", "updateTime": 1592663948975 },
        "OvenUpperCavity_DisplaySetUserButton1Time": { "value": "1", "updateTime": 1642158986086 },
        "XCat_ApplianceInfoSetSerialNumber": { "value": "xxxxxxxxx", "updateTime": 1642158986079 },
        "OvenUpperCavity_CycleSetDonenessAdjust": { "value": "0", "updateTime": 1642158986086 },
        "Relational_CapabilityModeTemperatures": { "value": "0", "updateTime": 1592663948975 },
        "XCat_PowerStatusEnergyMeasurementResults": { "value": "0", "updateTime": 1642158986079 },
        "Sys_DisplaySetZonedMessage": { "value": "0", "updateTime": 1592663948975 },
        "OvenUpperCavity_DisplaySetLightOn": { "value": "0", "updateTime": 1642443644576 },
        "XCat_DstOffset": { "value": "0", "updateTime": 1592663948975 },
        "Generic_UtilityID": { "value": "0", "updateTime": 1592663948975 },
        "OvenUpperCavity_CycleSetPreheatOn": { "value": "0", "updateTime": 1642158986086 },
        "Generic_SmartID": { "value": "0", "updateTime": 1592663948975 },
        "OvenUpperCavity_CycleSetCleanOvenMode": { "value": "0", "updateTime": 1642158986086 },
        "Relational_CapabilitySettings": { "value": "0", "updateTime": 1592663948975 },
        "ISP_PART_NUMBER": { "value": "W11569991", "updateTime": 1642327302255 },
        "OvenUpperCavity_CycleSetFrozenBakeFood": { "value": "0", "updateTime": 1642437699882 },
        "ConfigTime_SetDelayTimeMin": { "value": "0", "updateTime": 1592663948975 },
        "OvenUpperCavity_DisplaySetUserButton2Action": { "value": "0", "updateTime": 1642158986086 },
        "Generic_EnergyProfileSetting": { "value": "0", "updateTime": 1592663948975 },
        "ISP_DownloadEnd": { "value": "0", "updateTime": 1641282490066 },
        "SysHeader_RecipeSetRecipeTime": { "value": "0", "updateTime": 1642158986089 },
        "ISP_UpdateNotification": { "value": "1641252363", "updateTime": 1641282490066 },
        "OvenUpperCavity_CycleSetCommonModeProbe": { "value": "0", "updateTime": 1642158986086 },
        "OvenUpperCavity_TimeSetDelayTime": { "value": "0", "updateTime": 1642443644545 },
        "OvenUpperCavity_OpStatusCleanOven": { "value": "0", "updateTime": 1642158986086 },
        "OvenUpperCavity_CycleSetEasySteamFood": { "value": "0", "updateTime": 1642158986086 },
        "OvenUpperCavity_CycleSetBreadProof": { "value": "0", "updateTime": 1642158986086 },
        "Relational_EntityName": { "value": "0", "updateTime": 1592663948975 },
        "ISP_InstallEnd": { "value": "0", "updateTime": 1641282490066 },
        "ISP_TotalProcessInModule": { "value": "0", "updateTime": 1641282490066 },
        "OvenUpperCavity_DisplaySetMessage": { "value": "0", "updateTime": 1592663948975 },
        "OvenUpperCavity_AlertStatusMeatProbePluggedIn": { "value": "0", "updateTime": 1642158986086 },
        "TimezoneId": { "value": "America/Phoenix", "updateTime": 1595865616981 },
        "Sys_DisplayStatusBroilDisplayType": { "value": "2", "updateTime": 1642158986089 },
        "XCat_trid": { "value": "0", "updateTime": 1592663948975 },
        "orgId": { "value": "NAR", "updateTime": 1595805342488 },
        "XCat_RemoteSetRemoteControlEnable": { "value": "1", "updateTime": 1642158986079 },
        "UtcOffset": { "value": "-25200", "updateTime": 1595865616981 },
        "ConfigUint8Range_SetMin": { "value": "0", "updateTime": 1592663948975 },
        "OvenUpperCavity_CustomCycleSetId": { "value": "0", "updateTime": 1642158986086 },
        "OvenUpperCavity_CycleSetSteamPercent": { "value": "0", "updateTime": 1642158986086 },
        "OvenUpperCavity_CulinaryCtrSetId": { "value": "0", "updateTime": 1642158986086 },
        "XCat_ConfigSetMaxRelationalSteps": { "value": "0", "updateTime": 1592663948975 },
        "XCat_RemoteSetRebootAppliance": { "value": "0", "updateTime": 1642158986079 },
        "XCat_trid_result": { "value": "0", "updateTime": 1592663948975 },
        "OvenUpperCavity_CycleSetDoneness": { "value": "0", "updateTime": 1642158986086 },
        "ConfigTime_SetCookTimeMin": { "value": "0", "updateTime": 1592663948975 },
        "OvenLowerCavity_AlertStatusMeatProbePluggedIn": { "value": "4", "updateTime": 1612655437184 },
        "Sys_DisplaySetCompleteActionTimeout": { "value": "120", "updateTime": 1642158986089 },
        "Relational_CapabilityModeTimes": { "value": "0", "updateTime": 1592663948975 },
        "Generic_RatePlanID": { "value": "0", "updateTime": 1592663948975 },
        "Sys_OperationSetGreaseFilter": { "value": "0", "updateTime": 1642158986089 },
        "XCat_PowerStatusEnergyConsumption": { "value": "9", "updateTime": 1642443644588 },
        "XCat_DateTimeSetDateTimeSet": { "value": "2022-01-14T03:16:24+00:00", "updateTime": 1642158986079 },
        "OvenUpperCavity_TimeSetCookTimeSet": { "value": "0", "updateTime": 1642443644537 },
        "OvenUpperCavity_CycleSetEasyConvectFood": { "value": "0", "updateTime": 1642434057147 },
        "Relational_EnvelopeClose": { "value": "0", "updateTime": 1592663948975 },
        "Online": { "value": "1", "updateTime": 1642327293148 },
        "XCat_PowerSetRealTimePowerPublishStart": { "value": "0", "updateTime": 1642158986079 },
        "OvenUpperCavity_CycleSetMultiRackFood": { "value": "0", "updateTime": 1642158986086 },
        "Relational_ArrayClose": { "value": "0", "updateTime": 1592663948975 },
        "Sys_OperationSetSabbathModeEnabled": { "value": "0", "updateTime": 1642158986089 },
        "OvenUpperCavity__RecipeSetFacadeCookTime": { "value": "0", "updateTime": 1642158986086 },
        "Sys_OperationSetAlertToneVolume": { "value": "4", "updateTime": 1642158986089 },
        "body": {
            "value": "{node=3, nameSpaceID=255, Online=1, uri=API147_INDIGO_MGT_INDIGO_V1}",
            "updateTime": 1595718364528
        },
        "Sys_DisplaySetMessage": { "value": "0", "updateTime": 1592663948975 },
        "OvenUpperCavity_TimeSetCookTimeOperations": { "value": "0", "updateTime": 1642443644523 },
        "OvenUpperCavity_CycleSetConvectBakeFood": { "value": "0", "updateTime": 1642158986086 },
        "OvenUpperCavity_DisplaySetUserButton1Action": { "value": "0", "updateTime": 1642158986086 },
        "ConfigUint8Range_SetStep": { "value": "0", "updateTime": 1592663948975 },
        "OvenUpperCavity_CycleStatusOdometer": { "value": "554", "updateTime": 1642443644573 },
        "ModelNumber": { "value": "WOS72EC0HS01", "updateTime": 1642327296923 },
        "OvenUpperCavity_CycleSetFrozenCustomFood": { "value": "0", "updateTime": 1642158986086 },
        "ProjectReleaseNumber": { "value": "0", "updateTime": 1592663948975 },
        "ApplianceVersionNumber": { "value": "20", "updateTime": 1642327302255 },
        "OvenUpperCavity_CycleSetSlowCookingFood": { "value": "0", "updateTime": 1642158986086 },
        "ConfigCavity_SetTempMax": { "value": "0", "updateTime": 1592663948975 },
        "ConfigKitchenTimer_SetMax": { "value": "0", "updateTime": 1592663948975 },
        "OvenUpperCavity_DisplStatusMeatProbeDisplayTemp": { "value": "0", "updateTime": 1642158986086 },
        "XCat_RemoteSetRemoteDiagnosticsEnable": { "value": "0", "updateTime": 1642158986079 },
        "XCat_PowerStatusRealTimeVoltage": { "value": "0", "updateTime": 1642158986079 },
        "OvenLowerCavity_OpStatusCookTimeState": { "value": "4", "updateTime": 1614744414817 },
        "Sys_OperationSetConvertTime": { "value": "0", "updateTime": 1592663948975 },
        "XCat_WifiStatusRssiAntennaDiversity": { "value": "-61", "updateTime": 1642158986079 },
        "OvenUpperCavity_OpSetOperations": { "value": "0", "updateTime": 1642443644532 },
        "header": { "value": "{SAID=xxxxxxxxx}", "updateTime": 1595718364528 },
        "Sys_AlertStatusControlLockChangedByAppliance": { "value": "0", "updateTime": 1592663948975 },
        "XCat_PowerStatusPowerOutage": { "value": "0", "updateTime": 1642158986079 },
        "OvenUpperCavity_OpStatusCookTimeState": { "value": "0", "updateTime": 1642437699918 },
        "ConfigUint8Range_SetMax": { "value": "0", "updateTime": 1592663948975 },
        "OvenUpperCavity_DisplaySetUserButton3Action": { "value": "0", "updateTime": 1642158986086 },
        "OvenUpperCavity_CycleSetTargetTemp": { "value": "0", "updateTime": 1642443644549 },
        "XCat_PowerSetEnergyMeasurementStart": { "value": "0", "updateTime": 1642158986079 },
        "OvenUpperCavity_DisplStatusDisplayTemp": { "value": "0", "updateTime": 1642443644567 },
        "OvenUpperCavity__RecipeSetFacadeMode": { "value": "0", "updateTime": 1642158986086 },
        "XCat_WifiSetPublishApplianceState": { "value": "0", "updateTime": 1642158986079 },
        "OvenLowerCavity_CycleStatusOdometer": { "value": "54", "updateTime": 1598492874556 },
        "Sys_DisplaySetEnable24Hour": { "value": "0", "updateTime": 1642158986089 },
        "SAID": { "value": SAID, "updateTime": 1642327296923 },
        "XCat_WifiSetIspFirmwareDescriptionUrl": { "value": "0", "updateTime": 1592663948975 },
        "Relational_CycleMyCreation": { "value": "0", "updateTime": 1592663948975 },
        "OvenUpperCavity_OpSetMachineInstructCmpltAction": { "value": "0", "updateTime": 1642158986086 },
        "DstOffset": { "value": "0", "updateTime": 1595865616981 },
        "OvenUpperCavity_DisplaySetUserButton3Time": { "value": "1", "updateTime": 1642158986086 },
        "XCat_ApplianceInfoSetModelNumber": { "value": "WOS72EC0HS01", "updateTime": 1642158986079 },
        "DateTimeMode": { "value": "2", "updateTime": 1595865616981 },
        "XCat_WifiSetIspAuthorized": { "value": "0", "updateTime": 1642158986079 },
        "OvenUpperCavity_OpSetSabbathModeActive": { "value": "0", "updateTime": 1642158986086 },
        "OvenUpperCavity_TimeStatusCookTimeRemaining": { "value": "0", "updateTime": 1642434061628 },
        "OvenUpperCavity_CustomCycleSetStep": { "value": "0", "updateTime": 1642158986086 },
        "ConfigDisplay_SetZoneMessageLength": { "value": "0", "updateTime": 1592663948975 },
        "Sys_OperationSetCharcoalFilter": { "value": "0", "updateTime": 1642158986089 },
        "OvenLowerCavity_OpStatusDoorLocked": { "value": "4", "updateTime": 1613006545397 },
        "ISP_WIFI_VERSION": { "value": "1.cb.0", "updateTime": 1642327302255 },
        "OvenUpperCavity_OpStatusDoorOpen": { "value": "1", "updateTime": 1642360848734 },
        "Mwo_CycleStatusOdometer": { "value": "54", "updateTime": 1598492874562 },
        "ISP_DownloadStart": { "value": "0", "updateTime": 1641282490066 },
        "ISP_WIFI_PART_NUMBER": { "value": "W10835199", "updateTime": 1642327302255 },
        "OvenUpperCavity_OpSetCookTimeCompleteAction": { "value": "0", "updateTime": 1642443644557 },
        "OvenUpperCavity_CycleStatusMyCreationsId": { "value": "0", "updateTime": 1592875509959 },
        "ConfigKitchenTimer_SetSelect": { "value": "0", "updateTime": 1592663948975 },
        "ISP_InstallStart": { "value": "0", "updateTime": 1641282490066 },
        "OvenUpperCavity_CycleSetEasyProbe": { "value": "0", "updateTime": 1642158986086 }
    }
}
DATA3 = {
    "_id": SAID,
    "applianceId": SAID,
    "lastFullSyncTime": 1583550504221,
    "lastModified": 1643990060389,
    "attributes": {
        "OvenUpperCavity_DisplaySetUserInstructImageUrl": { "value": "0", "updateTime": 1643379086680 },
        "KitchenTimer01_StatusTimeRemaining": { "value": "0", "updateTime": 1643935427174 },
        "Sys_AlertStatusCustomerFaultCodeNotification": { "value": "0", "updateTime": 1583550504221 },
        "XCat_PowerStatusRealTimePower": { "value": "0", "updateTime": 1643379086684 },
        "XCat_PowerStatusRealTimeCurrent": { "value": "0", "updateTime": 1643379086684 },
        "ISPReasonCode": { "value": "0", "updateTime": 1583550504221 },
        "OvenUpperCavity_DisplaySetOnDemandId": { "value": "1", "updateTime": 1643379086680 },
        "OvenUpperCavity_TimeStatusPreheatTimeRemaining": { "value": "0", "updateTime": 1643379086680 },
        "sys-parser-type": { "value": "0", "updateTime": 1583550504221 },
        "Relational_CycleRecentCycles": { "value": "0", "updateTime": 1583550504221 },
        "Sys_DisplaySetLanguage": { "value": "0", "updateTime": 1643379086687 },
        "version": { "value": "1", "updateTime": 1643379081449 },
        "XCat_PersistentInfoVersion": { "value": "55", "updateTime": 1643379086684 },
        "SetDNSNames": { "value": "0", "updateTime": 1583550504221 },
        "XCat_SmartGridStatusSmartGridCompliant": { "value": "0", "updateTime": 1643379086684 },
        "Relational_ArrayOpen": { "value": "0", "updateTime": 1583550504221 },
        "Relational_to_Appliance": { "value": "0", "updateTime": 1583550504221 },
        "Relational_EnvelopeAction": { "value": "0", "updateTime": 1583550504221 },
        "OvenLowerCavity_OpStatusCleanOven": { "value": "4", "updateTime": 1584213454019 },
        "XCat_OdometerStatusTotalHours": { "value": "16851", "updateTime": 1643990060287 },
        "Sys_DisplaySetBrightnessPercent": { "value": "90", "updateTime": 1643379086687 },
        "XCat_SmartGridSetSmartGridEnable": { "value": "1", "updateTime": 1643379086684 },
        "Relational_EntityId": { "value": "0", "updateTime": 1583550504221 },
        "OvenUpperCavity_DisplaySetUserButton2Time": { "value": "1", "updateTime": 1643379086680 },
        "XCat_PersistentInfoSaid": { "value": SAID, "updateTime": 1643379086684 },
        "uid": { "value": "0", "updateTime": 1583550504221 },
        "PushTrigger": { "value": "0", "updateTime": 1583550504221 },
        "OvenUpperCavity_CycleSetSteamBakeFood": { "value": "0", "updateTime": 1643379086680 },
        "Sys_DisplaySetImage": { "value": "0", "updateTime": 1643379086687 },
        "ConfigTime_SetDelayTimeMax": { "value": "0", "updateTime": 1583550504221 },
        "OvenUpperCavity__RecipeSetFacadeDisplayTemp": { "value": "0", "updateTime": 1643379086680 },
        "Sys_DisplaySetCycleCompleteMessage": { "value": "0", "updateTime": 1583550504221 },
        "Sys_OperationSetControlLock": { "value": "0", "updateTime": 1643379086687 },
        "OvenUpperCavity_DisplaySetCycleCompleteMessage": { "value": "0", "updateTime": 1643379086680 },
        "XCat_WifiStatusIspCheck": { "value": "0", "updateTime": 1643379086684 },
        "OvenUpperCavity_OpStatusState": { "value": "0", "updateTime": 1643937625844 },
        "OvenLowerCavity_DisplStatusDisplayTemp": { "value": "4", "updateTime": 1584211375148 },
        "KitchenTimer01_SetTimeSet": { "value": "0", "updateTime": 1643935427176 },
        "XCat_WifiSetRebootWifiCommModule": { "value": "0", "updateTime": 1643379086684 },
        "XCat_ConfigSetApplianceCapability": { "value": "0", "updateTime": 1583550504221 },
        "ConfigCavity_SetTempDefault": { "value": "0", "updateTime": 1583550504221 },
        "XCat_PersistentInfoMacAddress": { "value": "88:e7:12:18:98:44", "updateTime": 1643379086684 },
        "Sys_OperationSetKeyPressToneVolume": { "value": "2", "updateTime": 1643379086687 },
        "M2MSubList": { "value": "0", "updateTime": 1583550504221 },
        "Relational_EntityClose": { "value": "0", "updateTime": 1583550504221 },
        "ConfigTime_SetCookTimeMax": { "value": "0", "updateTime": 1583550504221 },
        "XCat_OdometerStatusCycleCount": { "value": "185", "updateTime": 1643937625834 },
        "MAC_Address": { "value": "88:e7:12:18:98:44", "updateTime": 1643379070103 },
        "OvenUpperCavity_TimeStatusDelayTimeRemaining": { "value": "0", "updateTime": 1643379086680 },
        "Generic_Zip": { "value": "0", "updateTime": 1583550504221 },
        "Sys_AlertStatusCustomerFaultCode": { "value": "00,00", "updateTime": 1643379086687 },
        "XCat_TimeZoneId": { "value": "0", "updateTime": 1583550504221 },
        "Relational_EnvelopeOpen": {
            "value": "FD010005FE01000304FE02000101050000FE0200034D6F646554696D657300FE02000401FE03000101050001FE02000101050101FE0200034F76656E557070657243617669747900FE03000101050002FE020001010502010310000C02090100010000A8C00901000200000000FE02000201050201FE020001010502020310000C05090100010000A8C00901000200000000FE02000201050202FE020001010502030310000C06090100010000A8C00901000200000000FE02000201050203FE020001010502040310000C08090100010000A8C00901000200000000FE02000201050204FE020001010502050310000C09090100010000A8C00901000200000000FE02000201050205FE020001010502060310000C10090100010000A8C00901000200000000FE02000201050206FE020001010502070310000C18090100010000A8C00901000200000000FE02000201050207FE020001010502080310001002090100010000A8C0090100020000003CFE02000201050208FE020001010502090310001005090100010000A8C0090100020000003CFE02000201050209FE0200010105020A0310001006090100010000A8C0090100020000003CFE0200020105020AFE0200010105020B0310001007090100010000A8C0090100020000003CFE0200020105020BFE0200010105020C0310001008090100010000A8C0090100020000003CFE0200020105020CFE0200010105020D0310001009090100010000A8C0090100020000003CFE0200020105020DFE0200010105020E031000100A090100010000A8C0090100020000003CFE0200020105020EFE0200010105020F031000100B090100010000A8C0090100020000003CFE0200020105020FFE02000101050210031000100C090100010000A8C0090100020000003CFE02000201050210FE02000101050211031000100D090100010000A8C0090100020000003CFE02000201050211FE02000101050212031000100E090100010000A8C0090100020000003CFE02000201050212FE02000101050213031000100F090100010000A8C0090100020000003CFE02000201050213FE020001010502140310001010090100010000A8C0090100020000003CFE02000201050214FE020001010502150310001011090100010000A8C0090100020000003CFE02000201050215FE020001010502160310001012090100010000A8C0090100020000003CFE02000201050216FE020001010502170310001013090100010000A8C0090100020000003CFE02000201050217FE020001010502180310001014090100010000A8C0090100020000003CFE02000201050218FE020001010502190310001015090100010000A8C0090100020000003CFE02000201050219FE0200010105021A03100012020901000100002A3009010002000004B0FE0200020105021AFE0200010105021B03100012030901000100000E100901000200000258FE0200020105021BFE0200010105021C03100012040901000100002A3009010002000004B0FE0200020105021CFE0200010105021D0310001205090100010000A8C00901000200000258FE0200020105021DFE0200010105021E03100012060901000100002A300901000200000258FE0200020105021EFE0200010105021F03100012070901000100002A300901000200000258FE0200020105021FFE03000201050002FE02000201050101FE03000201050001FE02000201050000FE010002FD010005",
            "updateTime": 1599318365510
        },
        "OvenUpperCavity_DisplaySetEmbeddedUserInstructId": { "value": "0", "updateTime": 1643379086680 },
        "Relational_CapabilityTimeDefaults": { "value": "0", "updateTime": 1583550504221 },
        "XCat_WifiSetDeprovisionWifiCommModule": { "value": "0", "updateTime": 1643379086684 },
        "OvenUpperCavity_CycleSetConvectSlowRoastTime": { "value": "0", "updateTime": 1643379086680 },
        "GetSubscribeListVersion": { "value": "0", "updateTime": 1583550504221 },
        "OvenUpperCavity_CycleSetMeatProbeTargetTemp": { "value": "0", "updateTime": 1643937624350 },
        "Sys_AlertStatusNotification": { "value": "0", "updateTime": 1643379086687 },
        "ConfigKitchenTimer_SetMin": { "value": "0", "updateTime": 1583550504221 },
        "SysHeader_RecipeSetRecipeSummary": { "value": "0", "updateTime": 1643379086687 },
        "XCat_OdometerStatusRunningHours": { "value": "77", "updateTime": 1643379086684 },
        "XCat_DateTimeSetDateFormat": { "value": "0", "updateTime": 1643379086684 },
        "ccuri": { "value": "API144_COOKING_V55", "updateTime": 1643379070103 },
        "Sys_DisplaySetAutoShutOff": { "value": "0", "updateTime": 1583550504221 },
        "SerialNumber": { "value": "xxxxxxxxx", "updateTime": 1643379070103 },
        "OvenUpperCavity_DisplaySetCookingImageUrI": { "value": "00,00", "updateTime": 1643379086680 },
        "XCat_UtcOffset": { "value": "0", "updateTime": 1583550504221 },
        "XCat_WifiSetDisableWifiCommModule": { "value": "0", "updateTime": 1643379086684 },
        "KitchenTimer01_SetOperations": { "value": "1", "updateTime": 1643935427185 },
        "ConfigCavity_SetTempMin": { "value": "0", "updateTime": 1583550504221 },
        "OvenUpperCavity_DisplaySetZonedMessage": { "value": "0", "updateTime": 1643379086680 },
        "Sys_OperationSetConvertTemp": { "value": "0", "updateTime": 1583550504221 },
        "XCat_DateTimeMode": { "value": "0", "updateTime": 1583550504221 },
        "OvenUpperCavity_CycleSetMode": { "value": "0", "updateTime": 1599318368347 },
        "Sys_DisplaySetTempUnits": { "value": "1", "updateTime": 1643379086687 },
        "XCat_SmartGridSetSmartGridMode": { "value": "0,0,0,0,0", "updateTime": 1643379086684 },
        "OvenUpperCavity_AlertSetUserInstructToneSelect": { "value": "1", "updateTime": 1643379086680 },
        "XCat_PowerSetRealTimePowerPublishTiming": { "value": "0", "updateTime": 1643379086684 },
        "OvenUpperCavity_OpStatusDoorLocked": { "value": "0", "updateTime": 1643379086680 },
        "CC_URI": { "value": "API144_COOKING_V22", "updateTime": 1588406658196 },
        "XCat_InServiceDate": { "value": "0", "updateTime": 1583550504221 },
        "KitchenTimer01_StatusState": { "value": "0", "updateTime": 1643935427180 },
        "OvenUpperCavity_TimeStatusCycleTimeElapsed": { "value": "0", "updateTime": 1643937630333 },
        "OvenUpperCavity_CulinaryCtrSetQuantity": { "value": "0", "updateTime": 1643379086680 },
        "OvenUpperCavity_AlertSetToneSelect": { "value": "1", "updateTime": 1643379086680 },
        "SysHeader_RecipeSetRecipeId": { "value": "0", "updateTime": 1643379086687 },
        "ISP_REASON_CODE": { "value": "0", "updateTime": 1599373380328 },
        "OvenUpperCavity_CycleSetBrowning": { "value": "0", "updateTime": 1643379086680 },
        "OvenUpperCavity_DisplaySetEmbUsrInsCmpltAction": { "value": "0", "updateTime": 1643379086680 },
        "Sys_OperationSetQuietModeEnabled": { "value": "0", "updateTime": 1643935397094 },
        "M2MSubscribeListVersion": { "value": "0", "updateTime": 1583550504221 },
        "SubscribeClaimstate": { "value": "1", "updateTime": 1587965865187 },
        "OvenUpperCavity_CycleSetSousVide": { "value": "0", "updateTime": 1643379086680 },
        "OvenUpperCavity_CycleSetExtraCookingTime": { "value": "0", "updateTime": 1643379086680 },
        "OvenUpperCavity_CycleSetCommonMode": { "value": "0", "updateTime": 1643937624329 },
        "TimeZoneId": { "value": "America/Chicago", "updateTime": 1643967154286 },
        "Relational_EntityOpen": { "value": "0", "updateTime": 1583550504221 },
        "GetApplianceVersionNumber": { "value": "0", "updateTime": 1583550504221 },
        "OvenUpperCavity_DisplaySetUserButton1Time": { "value": "1", "updateTime": 1643379086680 },
        "XCat_ApplianceInfoSetSerialNumber": { "value": "xxxxxxxxx", "updateTime": 1643379086684 },
        "OvenUpperCavity_CycleSetDonenessAdjust": { "value": "0", "updateTime": 1643379086680 },
        "Relational_CapabilityModeTemperatures": { "value": "0", "updateTime": 1583550504221 },
        "XCat_PowerStatusEnergyMeasurementResults": { "value": "0", "updateTime": 1643379086684 },
        "Sys_DisplaySetZonedMessage": { "value": "0", "updateTime": 1583550504221 },
        "OvenUpperCavity_DisplaySetLightOn": { "value": "0", "updateTime": 1643937684496 },
        "XCat_DstOffset": { "value": "0", "updateTime": 1583550504221 },
        "Generic_UtilityID": { "value": "0", "updateTime": 1583550504221 },
        "OvenUpperCavity_CycleSetPreheatOn": { "value": "0", "updateTime": 1643379086680 },
        "Generic_SmartID": { "value": "0", "updateTime": 1583550504221 },
        "OvenUpperCavity_CycleSetCleanOvenMode": { "value": "0", "updateTime": 1643379086680 },
        "OvenUpperCavity_DisplaySetImageFolderUrl": { "value": "0", "updateTime": 1583550504221 },
        "Relational_CapabilityTimeTempConversion": { "value": "0", "updateTime": 1583550504221 },
        "Relational_CapabilitySettings": { "value": "0", "updateTime": 1583550504221 },
        "ISP_PART_NUMBER": { "value": "W00000000", "updateTime": 1643379074476 },
        "OvenUpperCavity_CycleSetFrozenBakeFood": { "value": "0", "updateTime": 1643379086680 },
        "ConfigTime_SetDelayTimeMin": { "value": "0", "updateTime": 1583550504221 },
        "OvenUpperCavity_DisplaySetUserButton2Action": { "value": "0", "updateTime": 1643379086680 },
        "Generic_EnergyProfileSetting": { "value": "0", "updateTime": 1583550504221 },
        "SysHeader_RecipeSetRecipeTime": { "value": "0", "updateTime": 1643379086687 },
        "OvenUpperCavity_CycleSetCommonModeProbe": { "value": "0", "updateTime": 1643379086680 },
        "OvenUpperCavity_TimeSetDelayTime": { "value": "0", "updateTime": 1643937624344 },
        "OvenUpperCavity_OpStatusCleanOven": { "value": "0", "updateTime": 1643379086680 },
        "OvenUpperCavity_CycleSetEasySteamFood": { "value": "0", "updateTime": 1643379086680 },
        "OvenUpperCavity_CycleSetBreadProof": { "value": "0", "updateTime": 1643379086680 },
        "Relational_EntityName": { "value": "0", "updateTime": 1583550504221 },
        "Generic_ISPBundleAttributes": { "value": "0", "updateTime": 1583550504221 },
        "OvenUpperCavity_AlertStatusMeatProbePluggedIn": { "value": "0", "updateTime": 1643379086680 },
        "TimezoneId": { "value": "America/Phoenix", "updateTime": 1595865538033 },
        "Sys_DisplayStatusBroilDisplayType": { "value": "2", "updateTime": 1643379086687 },
        "XCat_trid": { "value": "0", "updateTime": 1583550504221 },
        "orgId": { "value": "NAR", "updateTime": 1587965862989 },
        "XCat_RemoteSetRemoteControlEnable": { "value": "1", "updateTime": 1643379086684 },
        "UtcOffset": { "value": "-25200", "updateTime": 1595865538033 },
        "ConfigUint8Range_SetMin": { "value": "0", "updateTime": 1583550504221 },
        "OvenUpperCavity_CustomCycleSetId": { "value": "0", "updateTime": 1643379086680 },
        "OvenUpperCavity_CycleSetSteamPercent": { "value": "0", "updateTime": 1643379086680 },
        "OvenUpperCavity_CulinaryCtrSetId": { "value": "0", "updateTime": 1643379086680 },
        "XCat_RemoteSetRebootAppliance": { "value": "0", "updateTime": 1643379086684 },
        "XCat_trid_result": { "value": "0", "updateTime": 1583550504221 },
        "OvenUpperCavity_CycleSetDoneness": { "value": "0", "updateTime": 1643379086680 },
        "ConfigTime_SetCookTimeMin": { "value": "0", "updateTime": 1583550504221 },
        "OvenLowerCavity_AlertStatusMeatProbePluggedIn": { "value": "4", "updateTime": 1584210992058 },
        "Sys_DisplaySetCompleteActionTimeout": { "value": "120", "updateTime": 1643379086687 },
        "Relational_CapabilityModeTimes": { "value": "0", "updateTime": 1583550504221 },
        "Generic_RatePlanID": { "value": "0", "updateTime": 1583550504221 },
        "Sys_OperationSetGreaseFilter": { "value": "0", "updateTime": 1643379086687 },
        "XCat_PowerStatusEnergyConsumption": { "value": "115", "updateTime": 1643937625830 },
        "XCat_DateTimeSetDateTimeSet": { "value": "2022-02-04T03:32:34-06:00", "updateTime": 1643967154286 },
        "OvenUpperCavity_TimeSetCookTimeSet": { "value": "0", "updateTime": 1643937624341 },
        "OvenUpperCavity_CycleSetEasyConvectFood": { "value": "0", "updateTime": 1643379086680 },
        "Relational_EnvelopeClose": { "value": "0", "updateTime": 1583550504221 },
        "Online": { "value": "1", "updateTime": 1643379067460 },
        "XCat_PowerSetRealTimePowerPublishStart": { "value": "0", "updateTime": 1643379086684 },
        "OvenUpperCavity_CycleSetMultiRackFood": { "value": "0", "updateTime": 1643379086680 },
        "Relational_ArrayClose": { "value": "0", "updateTime": 1583550504221 },
        "Sys_OperationSetSabbathModeEnabled": { "value": "0", "updateTime": 1643379086687 },
        "OvenUpperCavity__RecipeSetFacadeCookTime": { "value": "0", "updateTime": 1643379086680 },
        "Sys_OperationSetAlertToneVolume": { "value": "4", "updateTime": 1643379086687 },
        "body": {
            "value": "{node=3, nameSpaceID=255, Online=1, uri=API147_INDIGO_MGT_INDIGO_V1}",
            "updateTime": 1587965864282
        },
        "OvenUpperCavity_TimeSetCookTimeOperations": { "value": "0", "updateTime": 1643937624332 },
        "OvenUpperCavity_CycleSetConvectBakeFood": { "value": "0", "updateTime": 1643379086680 },
        "OvenUpperCavity_DisplaySetUserButton1Action": { "value": "0", "updateTime": 1643379086680 },
        "ConfigUint8Range_SetStep": { "value": "0", "updateTime": 1583550504221 },
        "OvenUpperCavity_CycleStatusOdometer": { "value": "185", "updateTime": 1643937625848 },
        "ModelNumber": { "value": "WEG750H0HZ 0", "updateTime": 1643379070103 },
        "OvenUpperCavity_CycleSetFrozenCustomFood": { "value": "0", "updateTime": 1643379086680 },
        "ProjectReleaseNumber": { "value": "W10835199", "updateTime": 1583550465948 },
        "ApplianceVersionNumber": { "value": "15", "updateTime": 1643379074476 },
        "OvenUpperCavity_CycleSetSlowCookingFood": { "value": "0", "updateTime": 1643379086680 },
        "ConfigCavity_SetTempMax": { "value": "0", "updateTime": 1583550504221 },
        "ConfigKitchenTimer_SetMax": { "value": "0", "updateTime": 1583550504221 },
        "OvenUpperCavity_DisplStatusMeatProbeDisplayTemp": { "value": "0", "updateTime": 1643379086680 },
        "XCat_RemoteSetRemoteDiagnosticsEnable": { "value": "0", "updateTime": 1643379086684 },
        "XCat_PowerStatusRealTimeVoltage": { "value": "0", "updateTime": 1643379086684 },
        "Sys_OperationSetConvertTime": { "value": "0", "updateTime": 1583550504221 },
        "XCat_WifiStatusRssiAntennaDiversity": { "value": "-38", "updateTime": 1643379086684 },
        "OvenUpperCavity_OpSetOperations": { "value": "0", "updateTime": 1643937624335 },
        "header": { "value": "{SAID=xxxxxxxxx}", "updateTime": 1587965864282 },
        "Sys_AlertStatusControlLockChangedByAppliance": { "value": "0", "updateTime": 1583550504221 },
        "XCat_PowerStatusPowerOutage": { "value": "0", "updateTime": 1643379086684 },
        "OvenUpperCavity_OpStatusCookTimeState": { "value": "0", "updateTime": 1643379086680 },
        "ConfigUint8Range_SetMax": { "value": "0", "updateTime": 1583550504221 },
        "OvenUpperCavity_DisplaySetUserButton3Action": { "value": "0", "updateTime": 1643379086680 },
        "OvenUpperCavity_CycleSetTargetTemp": { "value": "0", "updateTime": 1643937624338 },
        "XCat_PowerSetEnergyMeasurementStart": { "value": "0", "updateTime": 1643379086684 },
        "OvenUpperCavity_DisplStatusDisplayTemp": { "value": "0", "updateTime": 1643937625840 },
        "OvenUpperCavity__RecipeSetFacadeMode": { "value": "0", "updateTime": 1643379086680 },
        "XCat_WifiSetPublishApplianceState": { "value": "0", "updateTime": 1643379086684 },
        "OvenLowerCavity_CycleStatusOdometer": { "value": "80", "updateTime": 1599358571842 },
        "Sys_DisplaySetEnable24Hour": { "value": "0", "updateTime": 1643379086687 },
        "SAID": { "value": SAID, "updateTime": 1643379070103 },
        "XCat_WifiSetIspFirmwareDescriptionUrl": { "value": "0", "updateTime": 1583550504221 },
        "Relational_CycleMyCreation": { "value": "0", "updateTime": 1583550504221 },
        "OvenUpperCavity_OpSetMachineInstructCmpltAction": { "value": "0", "updateTime": 1643379086680 },
        "Generic_ApplianceVersionNumber": { "value": "0", "updateTime": 1583550504221 },
        "DstOffset": { "value": "0", "updateTime": 1595865538033 },
        "OvenUpperCavity_DisplaySetUserButton3Time": { "value": "1", "updateTime": 1643379086680 },
        "XCat_ApplianceInfoSetModelNumber": { "value": "WEG750H0HZ 0", "updateTime": 1643379086684 },
        "DateTimeMode": { "value": "2", "updateTime": 1595865538033 },
        "XCat_WifiSetIspAuthorized": { "value": "0", "updateTime": 1643379086684 },
        "OvenUpperCavity_OpSetSabbathModeActive": { "value": "0", "updateTime": 1643379086680 },
        "OvenUpperCavity_TimeStatusCookTimeRemaining": { "value": "0", "updateTime": 1643379086680 },
        "OvenUpperCavity_CustomCycleSetStep": { "value": "0", "updateTime": 1643379086680 },
        "ConfigDisplay_SetZoneMessageLength": { "value": "0", "updateTime": 1583550504221 },
        "Sys_OperationSetCharcoalFilter": { "value": "0", "updateTime": 1643379086687 },
        "ISP_WIFI_VERSION": { "value": "1.c5.0", "updateTime": 1643379074476 },
        "OvenUpperCavity_OpStatusDoorOpen": { "value": "0", "updateTime": 1643937631851 },
        "Mwo_CycleStatusOdometer": { "value": "80", "updateTime": 1599358571879 },
        "ISP_WIFI_PART_NUMBER": { "value": "W10835199", "updateTime": 1643379074476 },
        "OvenUpperCavity_OpSetCookTimeCompleteAction": { "value": "0", "updateTime": 1643937624354 },
        "OvenUpperCavity_CycleStatusMyCreationsId": { "value": "0", "updateTime": 1585953016647 },
        "ConfigKitchenTimer_SetSelect": { "value": "0", "updateTime": 1583550504221 },
        "OvenUpperCavity_CycleSetEasyProbe": { "value": "0", "updateTime": 1643379086680 }
    }
}


def get_request_side_effect(url):
    if url.endswith("/getUserDetails"):
        return MockResponse(
            json.dumps(
                {
                    "accountId": ACCOUNT_ID,
                    "firstName": "Test",
                    "lastName": "Dummy",
                    "email": "testdummy@testing.com",
                }
            ),
            200,
        )
    if url.endswith(f"/appliancebyaccount/{ACCOUNT_ID}"):
        return MockResponse(
            json.dumps(
                {ACCOUNT_ID: {"12345": [{"APPLIANCE_NAME": AC_NAME, "SAID": SAID}]}}
            ),
            200,
        )
    if url.endswith(f"/appliance/{SAID}"):
        return MockResponse(json.dumps({}), 200)

    raise Exception(f"Unexpected url: {url}")


async def test_attributes(caplog, aio_httpclient):
    caplog.set_level(logging.DEBUG)
    auth = MagicMock()

    aio_httpclient.get.return_value = MockResponse(json.dumps(DATA1), 200)

    oven = Oven(BackendSelectorMock(), auth, SAID, None)
    await oven.connect()
    assert oven.get_online() is True
    assert oven.get_door_opened() == False
    assert oven.get_control_locked() == False
    assert oven.get_sabbath_mode() == False
    assert oven.get_display_brightness_percent() == 90
    assert oven.get_oven_cavity_exists(Cavity.Upper) == True
    assert oven.get_oven_cavity_exists(Cavity.Lower) == False
    assert oven.get_light(Cavity.Upper) == False
    assert oven.get_meat_probe_status(Cavity.Upper) == False
    assert oven.get_cook_time(Cavity.Upper) == 81
    assert oven.get_temp(Cavity.Upper) == 37.7
    assert oven.get_target_temp(Cavity.Upper) == 176.6
    assert oven.get_cavity_state(Cavity.Upper) == CavityState.Preheating
    assert oven.get_cook_mode(Cavity.Upper) == CookMode.Bake
    await oven.disconnect()

    aio_httpclient.get.return_value = MockResponse(json.dumps(DATA2), 200)
    await oven.connect()
    assert oven.get_online() is True
    assert oven.get_door_opened() == True
    assert oven.get_control_locked() == True
    assert oven.get_sabbath_mode() == False
    assert oven.get_display_brightness_percent() == 70
    assert oven.get_oven_cavity_exists(Cavity.Upper) == True
    assert oven.get_oven_cavity_exists(Cavity.Lower) == False
    assert oven.get_light(Cavity.Upper) == False
    assert oven.get_meat_probe_status(Cavity.Upper) == False
    assert oven.get_cook_time(Cavity.Upper) == 0
    assert oven.get_temp(Cavity.Upper) == 0.0
    assert oven.get_target_temp(Cavity.Upper) == 0.0
    assert oven.get_cavity_state(Cavity.Upper) == CavityState.Standby
    assert oven.get_cook_mode(Cavity.Upper) == CookMode.Standby
    await oven.disconnect()

    aio_httpclient.get.return_value = MockResponse(json.dumps(DATA3), 200)
    await oven.connect()
    assert oven.get_online() is True
    assert oven.get_door_opened() == False
    assert oven.get_control_locked() == False
    assert oven.get_sabbath_mode() == False
    assert oven.get_display_brightness_percent() == 90
    assert oven.get_oven_cavity_exists(Cavity.Upper) == True
    assert oven.get_oven_cavity_exists(Cavity.Lower) == False
    assert oven.get_light(Cavity.Upper) == False
    assert oven.get_meat_probe_status(Cavity.Upper) == False
    assert oven.get_cook_time(Cavity.Upper) == 0
    assert oven.get_temp(Cavity.Upper) == 0.0
    assert oven.get_target_temp(Cavity.Upper) == 0.0
    assert oven.get_cavity_state(Cavity.Upper) == CavityState.Standby
    assert oven.get_cook_mode(Cavity.Upper) == CookMode.Standby
    await oven.disconnect()

async def test_setters(caplog, aio_httpclient):
    caplog.set_level(logging.DEBUG)
    auth = MagicMock()

    aio_httpclient.get.return_value = MockResponse(json.dumps(DATA2), 200)
    aio_httpclient.post.return_value = MockResponse("", 200)

    cmd_data = {
        "header": {"said": SAID, "command": "setAttributes"},
    }

    oven = Oven(BackendSelectorMock(), auth, SAID, None)
    await oven.connect()
    await oven.set_control_locked(True)
    cmd_data["body"] = {"Sys_OperationSetControlLock": "1"}
    aio_httpclient.post.assert_called_once_with(ANY, json=cmd_data)

    aio_httpclient.post.reset_mock()
    await oven.set_control_locked(False)
    cmd_data["body"] = {"Sys_OperationSetControlLock": "0"}
    aio_httpclient.post.assert_called_once_with(ANY, json=cmd_data)

    aio_httpclient.post.reset_mock()
    await oven.set_light(True)
    cmd_data["body"] = {"OvenUpperCavity_DisplaySetLightOn": "1"}

    aio_httpclient.post.reset_mock()
    await oven.set_cook(mode=CookMode.Bake, cavity=Cavity.Upper, target_temp=260)
    cmd_data["body"] = {"OvenUpperCavity_CycleSetCommonMode": "2", "OvenUpperCavity_CycleSetTargetTemp": 2600, "OvenUpperCavity_OpSetOperations": 2}
    aio_httpclient.post.assert_called_once_with(ANY, json=cmd_data)

    aio_httpclient.post.reset_mock()
    await oven.set_bake(cavity=Cavity.Upper, target_temp=260)
    cmd_data["body"] = {"OvenUpperCavity_CycleSetCommonMode": "2", "OvenUpperCavity_CycleSetTargetTemp": 2600, "OvenUpperCavity_OpSetOperations": 2}
    aio_httpclient.post.assert_called_once_with(ANY, json=cmd_data)

    aio_httpclient.post.reset_mock()
    await oven.set_cook(mode=CookMode.Broil, cavity=Cavity.Upper, target_temp=260)
    cmd_data["body"] = {"OvenUpperCavity_CycleSetCommonMode": "8", "OvenUpperCavity_CycleSetTargetTemp": 2600, "OvenUpperCavity_OpSetOperations": 2}
    aio_httpclient.post.assert_called_once_with(ANY, json=cmd_data)

    aio_httpclient.post.reset_mock()
    await oven.set_broil(cavity=Cavity.Upper, target_temp=260)
    cmd_data["body"] = {"OvenUpperCavity_CycleSetCommonMode": "8", "OvenUpperCavity_CycleSetTargetTemp": 2600, "OvenUpperCavity_OpSetOperations": 2}
    aio_httpclient.post.assert_called_once_with(ANY, json=cmd_data)

    aio_httpclient.post.reset_mock()
    await oven.set_convect_broil(cavity=Cavity.Upper, target_temp=260)
    cmd_data["body"] = {"OvenUpperCavity_CycleSetCommonMode": "9", "OvenUpperCavity_CycleSetTargetTemp": 2600, "OvenUpperCavity_OpSetOperations": 2}
    aio_httpclient.post.assert_called_once_with(ANY, json=cmd_data)

    aio_httpclient.post.reset_mock()
    await oven.set_convect_bake(cavity=Cavity.Upper, target_temp=260)
    cmd_data["body"] = {"OvenUpperCavity_CycleSetCommonMode": "6", "OvenUpperCavity_CycleSetTargetTemp": 2600, "OvenUpperCavity_OpSetOperations": 2}
    aio_httpclient.post.assert_called_once_with(ANY, json=cmd_data)

    aio_httpclient.post.reset_mock()
    await oven.set_keep_warm(cavity=Cavity.Upper, target_temp=100)
    cmd_data["body"] = {"OvenUpperCavity_CycleSetCommonMode": "24", "OvenUpperCavity_CycleSetTargetTemp": 1000, "OvenUpperCavity_OpSetOperations": 2}
    aio_httpclient.post.assert_called_once_with(ANY, json=cmd_data)

    aio_httpclient.post.reset_mock()
    await oven.set_air_fry(cavity=Cavity.Upper, target_temp=260)
    cmd_data["body"] = {"OvenUpperCavity_CycleSetCommonMode": "41", "OvenUpperCavity_CycleSetTargetTemp": 2600, "OvenUpperCavity_OpSetOperations": 2}
    aio_httpclient.post.assert_called_once_with(ANY, json=cmd_data)

    aio_httpclient.post.reset_mock()
    await oven.set_convect_roast(cavity=Cavity.Upper, target_temp=260)
    cmd_data["body"] = {"OvenUpperCavity_CycleSetCommonMode": "16", "OvenUpperCavity_CycleSetTargetTemp": 2600, "OvenUpperCavity_OpSetOperations": 2}
    aio_httpclient.post.assert_called_once_with(ANY, json=cmd_data)

    aio_httpclient.post.reset_mock()
    await oven.stop_cook(Cavity.Upper)
    cmd_data["body"] = {"OvenUpperCavity_OpSetOperations": 1}
    aio_httpclient.post.assert_called_once_with(ANY, json=cmd_data)

    aio_httpclient.post.reset_mock()
    await oven.set_sabbath_mode(True)
    cmd_data["body"] = {"Sys_OperationSetSabbathModeEnabled": "1"}
    aio_httpclient.post.assert_called_once_with(ANY, json=cmd_data)

    aio_httpclient.post.reset_mock()
    await oven.set_display_brightness_percent(50)
    cmd_data["body"] = {"Sys_DisplaySetBrightnessPercent": "50"}
    aio_httpclient.post.assert_called_once_with(ANY, json=cmd_data)

    await oven.disconnect()
