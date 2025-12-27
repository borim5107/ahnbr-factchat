#!/usr/bin/env python3
# run_chat.py
"""
[의도]
- factchat_client_min.py가 정상 동작하는지 빠르게 확인하기 위한 실행 스크립트
- 라이브러리(FactChatClient)를 import해서 실제 API 호출을 1회 수행한다

[역할]
- 테스트/디버깅용 진입점(entry point)
- 비즈니스 로직이나 추상화는 절대 여기서 하지 않는다
- 모든 핵심 로직은 factchat_client_min.py에만 둔다

[사용 시나리오]
- 환경변수(FACTCHAT_API_KEY)가 제대로 설정되었는지 확인
- router / payload / call 전체 경로가 문제없이 연결되는지 smoke test
"""

from factchat_client_min import FactChatClient

# FactChatClient 인스턴스 생성
# (API Key, Base URL 등은 환경변수에서 자동 로드됨)
fc = FactChatClient()

# 최소 요청: 모델 + 단일 사용자 입력
# 성공 시 "pong" 또는 모델 응답 텍스트가 출력되어야 한다
res = fc.call(
    model="gpt-5-mini",
    user_text="ping"
)

# 정규화된 응답 중, 최종 텍스트만 출력
print(res.text)
