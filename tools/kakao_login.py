"""카카오 리프레시 토큰을 처음 한 번 받는 도우미 (내 PC에서 실행).

1) python tools/kakao_login.py  → 안내되는 주소를 브라우저에서 열어 로그인·동의
2) 주소창이 바뀌면 '?code=' 뒤의 값을 복사해 붙여넣기
3) 출력된 REFRESH_TOKEN 을 GitHub Secrets 의 KAKAO_REFRESH_TOKEN 에 저장
"""
import json
import urllib.parse
import urllib.request

REST_KEY = input("카카오 REST API 키: ").strip()
REDIRECT = input("등록한 Redirect URI (예: https://localhost/oauth): ").strip()
SECRET = input("Client Secret (사용 안 하면 그냥 엔터): ").strip()

q = urllib.parse.urlencode({"client_id": REST_KEY, "redirect_uri": REDIRECT,
                            "response_type": "code", "scope": "talk_message"})
print("\n아래 주소를 브라우저에서 열고 로그인·동의하세요:\n")
print("https://kauth.kakao.com/oauth/authorize?" + q)
code = input("\n이동된 주소의 code= 뒤의 값: ").strip()

data = {"grant_type": "authorization_code", "client_id": REST_KEY,
        "redirect_uri": REDIRECT, "code": code}
if SECRET:
    data["client_secret"] = SECRET
req = urllib.request.Request("https://kauth.kakao.com/oauth/token",
                             data=urllib.parse.urlencode(data).encode())
try:
    res = json.load(urllib.request.urlopen(req))
    print("\nREFRESH_TOKEN =", res["refresh_token"])
except urllib.error.HTTPError as e:
    print("실패:", e.read().decode())
