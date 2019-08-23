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

    # EndPoints
    LONG_POLLING = "/P4"
    AUTH_QUERY_PATH = "/api/v4/TalkService.do"
    AUTH_REGISTRATION = "/api/v4p/rs"


class LINE(object):
    
    def __init__(self):
        self.thrift = thriftpy2.load("line.thrift")

        self.transport = THttpClient(Config.HOST)
        self.transport.setCustomHeaders({
            "User-Agent": Config.UA,
            "X-Line-Application": Config.LA,
            "X-Line-Carrier": Config.CARRIER,
        })
        self.protocol = TCompactProtocol(self.transport)
        self.transport.open()
        self.client = TClient(self.thrift.Service, self.protocol)

        self.auth_session = requests.session()


    def loginWithQrCode(self, keepLoggedIn=True, systemName=None, appName=None):
        if systemName is None:
            systemName=Config.SYSTEM_NAME
        if appName is None:
            appName=Config.LA

        self.transport.path = Config.AUTH_QUERY_PATH
        res = self.client.getAuthQrcode(True, systemName)
        print(res)