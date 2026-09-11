# 파이썬함수연습2.py

def connectURI(server, port):
    #f-string을 이용하여 문자열을 생성
    strUrl = f"http://{server}:{port}"
    return strUrl

print(connectURI("kpc.com", 8080))
print("aaa  bbb ccc")

