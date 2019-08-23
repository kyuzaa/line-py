import requests, json, os

import thriftpy2
from thriftpy2.http import THttpClient
from thriftpy2.protocol import TCompactProtocol
from thriftpy2.thrift import TClient

class Config(object):
    HOST = "https://legy-jp.line.naver.jp:443"


    # Client
    LA = "IOSIPAD\t9.12.0\tiOS\t12.4"
    UA = "Line/9.12.0 iPad7,3 12.4"
    CARRIER = "51089, 1-0"
    SYSTEM_NAME = "LINE"
    IP_ADDR = "8.8.8.8"

    # EndPoints
    LONG_POLLING = "/P4"
    LINE_CERTIFICATE_PATH = "/Q"
    AUTH_QUERY_PATH = "/api/v4/TalkService.do"
    AUTH_REGISTRATION = "/api/v4p/rs"
    LINE_API_QUERY_PATH_FIR = "/S4"


class LINE(object):
    
    def __init__(self):
        self.thrift = thriftpy2.load("line.thrift")

        self.transport = THttpClient(Config.HOST)
        self.transport.setCustomHeaders({
            "User-Agent": Config.UA,
            "X-Line-Application": Config.LA,
            "X-Line-Carrier": Config.CARRIER,
            "X-LHM": "POST",
            "X-lal": "ja-JP_JP"
        })
        self.protocol = TCompactProtocol(self.transport)
        self.transport.open()
        self.client = TClient(self.thrift.Service, self.protocol)


    def loginWithQrCode(self, keepLoggedIn=True, systemName=None, appName=None):
        if systemName is None:
            systemName = Config.SYSTEM_NAME
        if appName is None:
            appName = Config.LA

        self.transport.path = Config.AUTH_QUERY_PATH
        res = self.client.getAuthQrcode(True, systemName)
        print("line://au/q/" + res.verifier)

        headers = {
            "User-Agent": Config.UA,
            "X-Line-Application": Config.LA,
            "X-Line-Carrier": Config.CARRIER,
            "x-lal": "ja-US_US",
            "x-lpqs": Config.AUTH_QUERY_PATH,
            "X-Line-Access": res.verifier
        }
        verifier = requests.get(Config.HOST + Config.LINE_CERTIFICATE_PATH, headers=headers).json()["result"]["verifier"]

        try:
            self.transport.path = Config.AUTH_REGISTRATION
            LR = self.thrift.LoginRequest()
            LR.type = self.thrift.LoginType.QRCODE
            LR.identityProvider = self.thrift.IdentityProvider.LINE
            LR.keepLoggedIn = keepLoggedIn
            LR.accessLocation = Config.IP_ADDR
            LR.verifier = verifier
            LR.e2eeVersion = 1
        except:
            raise Exception('Login failed')

        result = self.client.loginZ(LR)
        if result.type == LoginResultType.SUCCESS:
            if result.authToken is not None:
                self.loginWithAuthToken(result.authToken, appName)
            else:
                return False
        else:
            raise Exception('Login failed')
        print(result)


    def loginWithAuthToken(self, authToken=None, appName=None):
        if authToken is None:
            raise Exception('Please provide Auth Token')
        if appName is None:
            appName = Config.LA
        self.transport.setCustomHeaders({
            "User-Agent": Config.UA,
            "X-Line-Carrier": Config.CARRIER,
            "X-Line-Application": Config.LA,
            "X-Line-Access": authToken
        })
        self.protocol = TCompactProtocol(self.transport)
        self.transport.open()
        self.client = TClient(self.thrift.Service, self.protocol)
        self.transport.path = Config.LINE_API_QUERY_PATH_FIR
        self.authToken = authToken
        print(self.client.getProfile())