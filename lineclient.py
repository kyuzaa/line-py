import requests, rsa, thriftpy2
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
        self.certificate = None


    def __loadSession(self):
    	# Talk Service
        self.transport.setCustomHeaders({
            "User-Agent": Config.UA,
            "X-Line-Carrier": Config.CARRIER,
            "X-Line-Application": Config.LA,
            "X-Line-Access": self.authToken
        })

        self.transport.path = Config.LINE_API_QUERY_PATH_FIR
        self.talk = TClient(self.thrift.Service, self.protocol)
        self.profile = self.talk.getProfile()
        print("[Login success] "+ self.profile.displayName)

        self.transport.path = Config.LONG_POLLING
        self.poll = TClient(self.thrift.Service, self.protocol)
        self.revision = self.poll.getLastOpRevision()

    def loginWithQrCode(self):

        self.transport.path = Config.AUTH_QUERY_PATH
        res = self.client.getAuthQrcode(True, Config.SYSTEM_NAME)
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
            LR.keepLoggedIn = True
            LR.accessLocation = Config.IP_ADDR
            LR.verifier = verifier
            LR.e2eeVersion = 1
            result = self.client.loginZ(LR)
        except:
            raise Exception('Login failed')

        if result.type == LoginResultType.SUCCESS:
            if result.authToken is not None:
                self.loginWithAuthToken(result.authToken)
            else:
                return False
        else:
            raise Exception('Login failed')


    def loginWithCredential(self, mail, password, certificate=None):

        self.transport.path = Config.AUTH_QUERY_PATH
        RSAKey = self.client.getRSAKeyInfo(self.thrift.IdentityProvider.LINE)
        message = (chr(len(RSAKey.sessionKey))+RSAKey.sessionKey+chr(len(mail))+mail+chr(len(password))+password).encode('utf-8')
        pub_key = rsa.PublicKey(int(RSAKey.nvalue, 16), int(RSAKey.evalue, 16))
        crypto = rsa.encrypt(message, pub_key).hex()

        try:
            with open(mail + '.crt', 'r') as f:
                self.certificate = f.read()
        except:
            if certificate is not None:
                self.certificate = certificate

        LR = self.thrift.LoginRequest()
        LR.type = self.thrift.LoginType.ID_CREDENTIAL
        LR.identityProvider = self.thrift.IdentityProvider.LINE
        LR.identifier = RSAKey.keynm
        LR.password = crypto
        LR.keepLoggedIn = True
        LR.accessLocation = Config.IP_ADDR
        LR.systemName = Config.SYSTEM_NAME
        LR.certificate = self.certificate
        LR.e2eeVersion = 1

        self.transport.path = Config.AUTH_REGISTRATION
        result = self.client.loginZ(LR)
        
        if result.type == self.thrift.LoginResultType.REQUIRE_DEVICE_CONFIRM:
            print("Enter pincode: "+result.pinCode)

            headers = {
                "User-Agent": Config.UA,
                "X-Line-Application": Config.LA,
                "X-Line-Carrier": Config.CARRIER,
                "X-Line-Access": result.verifier
            }
            verifier = requests.get(Config.HOST + Config.LINE_CERTIFICATE_PATH, headers=headers).json()["result"]["verifier"]

            try:
                LR = self.thrift.LoginRequest()
                LR.type = self.thrift.LoginType.QRCODE
                LR.keepLoggedIn = True
                LR.verifier = verifier
                LR.e2eeVersion = 1
                result = self.client.loginZ(LR)
            except:
                raise Exception('Login failed')
            
            if result.type == self.thrift.LoginResultType.SUCCESS:
                if result.certificate is not None:
                    with open(mail + '.crt', 'w') as f:
                        f.write(result.certificate)
                    self.certificate = result.certificate
                if result.authToken is not None:
                    self.loginWithAuthToken(result.authToken)
                else:
                    return False
            else:
                raise Exception('Login failed')

        elif result.type == self.thrift.LoginResultType.REQUIRE_QRCODE:
            self.loginWithQrCode()
            pass

        elif result.type == self.thrift.LoginResultType.SUCCESS:
            self.certificate = result.certificate
            self.loginWithAuthToken(result.authToken)

    def loginWithAuthToken(self, authToken=None):
        if authToken is None:
            raise Exception('Please provide Auth Token')

        self.authToken = authToken
        self.__loadSession()
