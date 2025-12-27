# test_factchat.py
# bin/env python3
# 테스트 스크립트: FactChat API에 POST 요청 보내기
"""
[목적]
- FactChat API가 살아있는지
- API Key가 유효한지
- path 엔드포인트가 동작하는지

[의도]
- path, model 바꿔가며 model-path 조합 실측 -> route 설계 근거
"""

"""
[확정된 사항]
- OpenAI 계열(gpt-*), Claude 계열(claude-*) 확인 완료

[미해결 / 보류 이슈]
- Google Gemini 계열:
  - 현재 계정에 gemini-* 모델이 없음
  - google/models/* 엔드포인트에서
    messages/contents 스키마 충돌 발생
  - 서버 측 라우팅/검증 레이어 이슈로 판단 → 클라이언트에서 해결 불가
  - 추후 계정에 Gemini 열리면 재검증 필요

- 나머지 모델(grok, sonar, gemma, fireworks/oss 등)은
  테스트 비용/피로도 고려해 추후 작업으로 미룸
"""
import os # 환경변수에서 API 키와 베이스 URL 가져오기 위해
import sys
import requests # HTTP POST 요청을 보내기 위해 

# 모델 이름 인자에서 가져오기, 없으면 기본값 & 아래 코드 실행
default = "gpt-5-mini"
if len(sys.argv) > 1:
    model = sys.argv[1]
else:
    model = default

# 환경변수에서 베이스 URL과 API 키 가져오기
base = os.environ.get("FACTCHAT_BASE_URL", "https://factchat-cloud.mindlogic.ai/v1/api").rstrip("/") # 중복 슬래시 제거
key = os.environ["FACTCHAT_API_KEY"] 

path = "openai/images/generate" # 엔드포인트 경로 -- test할때마다 변경하기 ⚪⚪⚪

url = f"{base}/{path}" # 전체 URL 구성
# 인증 + JSON 요청을 위한 HTTP 헤더기기
headers = {"Authorization": f"Bearer {key}", # -> API 키 전달
            "Content-Type": "application/json"  # -> JSON 바디 전송
            } 
# 테스트 요청용 바디
payload = {
        "model": model,
        "prompt": "ping test image",
        "size": "1024x1024",
    }

# FactChat API에 POST 요청 보내기
r = requests.post(url, headers=headers, json=payload, timeout=180) # POST 요청 보내기
print(r.status_code) # 서버 응답 상태 확인
print(r.text[:500]) # 응답 내용 일부 확인
# debug용 출력
print("Base:", base) 
print("Model:", payload["model"])
print("Path:", path)
print("Payload:", payload)

# ============================================
# 테스트 결과 메모
# ============================================

# gpt-* path: openai/chat/completions (✅)
'''
payload = {
    "model": model,
    "messages": [{"role": "user", "content": "ping"}] 
} 
'''
# claude-* path: anthropic/messages (✅) 
'''
payload = {
    "model": model,
    "max_tokens": 32,
    "messages": [{"role": "user", "content": "ping"}] 
} 
'''
# gpt-image-* path: openai/images/generate (✅)
'''
 payload = {
        "model": model,
        "prompt": "ping test image",
        "size": "1024x1024",
    }
'''