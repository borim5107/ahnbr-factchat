# factchat_client_min.py 
# bin/env python3
# FactChat api를 최소한으로 쓰기 위한 클라이언트 구현
"""
[목적]
- model 이름만으로 provider / endpoint / payload 스키마 차이를 숨김

[의도]
- FactChat API를 "모델 이름만 바꿔서" 쓰기 위한 최소 클라이언트
- OpenAI / Claude만 먼저 안정적으로 지원
- provider별로 엔드포인트(path)와 payload 스키마가 다르기 때문에
  이를 코드 내부에서 명시적으로 분기한다 (-> router)

[설계 원칙]
- model → router → (path, provider) 결정
- provider → payload 스키마 결정
- 응답은 모두 LLMResponse로 정규화
- 나머지 모델(grok, sonar, gemma 등)은 나중에 router에 분기 추가
"""

"""
[현재 동작 범위]
- gpt-*  → openai/chat/completions + messages
- claude-* → anthropic/messages + messages (+ max_tokens)
- 응답은 모두 LLMResponse(text, model, usage, raw)로 정규화

[확인된 이슈 / 제약]
- provider별 응답 포맷이 완전히 동일하지 않음
  → 현재는 OpenAI chat.completion 형태를 기준으로 파싱
  → Claude 전용 파싱 로직은 추후 필요 시 추가
- usage / finish_reason은 provider에 따라 없을 수 있음

[TODO]
- router(): 기타 모델 라우팅 분기 확장 
  - gpt-image-*, grok-*, sonar-*, gemma-* 등
- build_payload(): 기타 모델 페이로드 빌드 분기 확장
- _parse_result(): provider별 응답 파싱 분기 확장
- call(): 네트워크 에러 메시지 정규화
- 선택적으로 CLI 진입점(__main__) 추가
"""



from __future__ import annotations 
import os
import requests
from dataclasses import dataclass
from typing import Optional, Dict, Any, Tuple, List

DEFAULT_BASE = "https://factchat-cloud.mindlogic.ai/v1/api"

@dataclass
class LLMResponse:  
    """ 
    모든 model response -> 공통 포맷으로 정규화 
    의도:
    - OpenAI / Claude / (추후 다른 모델) 응답 구조가 달라도
      상위 코드에서는 항상 동일한 인터페이스(text, usage 등)로 다루기 위함
    - raw 필드를 남겨두어, provider별 응답 차이를 나중에 분석/디버깅 가능하게 함
    """

    text: str   # normalized output
    model: str
    usage: Dict[str, int]   # token usage
    finish_reason: Optional[str]     # 'stop', 'length', 'content_filter', etc. # None if not applicable
    raw: Dict[str, Any]     # API 응답 JSON 원본

class FactChatClient:
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, timeout: int = 60):
        self.api_key = api_key or os.environ.get("FACTCHAT_API_KEY")
        if not self.api_key:
            raise RuntimeError("FACTCHAT_API_KEY missing")
        
        # base url 인자 있으면 우선 사용, 없으면 환경변수, 그래도 없으면 기본값
        self.base_url = (base_url or os.environ.get("FACTCHAT_BASE_URL") or DEFAULT_BASE).rstrip('/')
        self.timeout = timeout

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}", 
            "Content-Type": "application/json"
            }

    def router(self, model: str) -> Tuple[str, str]:
          """
            model 이름을 기준으로
            - 어떤 엔드포인트(path)로 보낼지
            - 어떤 provider(openai / anthropic)를 쓸지
            를 결정하는 함수

            의도:
            - 외부에서는 model 문자열만 신경 쓰게 하고
            - 엔드포인트 차이('openai/chat/completions' vs 'anthropic/messages')는 이 함수 안으로 완전히 숨긴다
            - 나중에 모델이 추가되면 if/elif 분기만 늘리면 됨
        """
        m = model.lower()
        if m.startswith("claude-"):
            return "anthropic/messages", "anthropic"
        
        elif m.startswith("gpt-"):
            return "openai/chat/completions", "openai" 

        else:
            raise ValueError(f"Unsupported model: {model}")

        # 기타 모델 라우팅 규칙 추가 가능

    def build_payload(self, model: str, user_text: str, **kwargs: Any) -> Dict[str, Any]:
        """ 
        provider 별로 body schema 맞춰 빌드 
        
        의도: 
        - router에서 결정된 provider를 기준으로 payload 구조를 명시적으로 분기
        - 'messages' / 'max_tokens' 같은 차이를 이 함수 안에서만 처리
        -  call()에서는 payload 구조를 신경 쓰지 않게 함
        """
        _, provider = self.router(model)

        if provider == "anthropic":
            payload: Dict[str, Any] = {
                "model": model,
                "max_tokens": kwargs.pop("max_tokens", 256),
                "messages": [{"role": "user", "content": user_text}]
            }
            payload.update(kwargs)
            return payload

        elif provider == "openai":
            payload: Dict[str, Any] = {
                "model": model,
                "messages": [{"role": "user", "content": user_text}],
            }
            payload.update(kwargs)
            return payload

        else:
            raise ValueError(f"Unsupported provider: {provider}")

        # 기타 모델 페이로드 빌드 규칙 추가 가능

    def _parse_result(self, provider: str, data: Dict[str, Any]) -> LLMResponse:
        """
        chatgpt-* 형태 기준으로 파싱
        claude-* 형태 등 기타 모델 응답 포맷이 다르면 provider == 'anthropic' 분기에서 추가 파싱
        """

        if "choices" in data and data.get("choices"):
            msg = data["choices"][0].get("message", {}) or {}
            text = msg.get("content", "") or ""
            finish = data["choices"][0].get("finish_reason", None)
            usage = data.get("usage", {}) or {}
            model = data.get("model", "") or ""
            return LLMResponse(text=text, model=model, usage=usage, finish_reason=finish, raw=data)
        
        # Claude 응답 포맷이 다르면 여기서 추가 파싱(필요 시 확장)

        # debug 용으로 원본 데이터 통째로 반환
        return LLMResponse(text=str(data), model=data.get("model", ""), usage=data.get("usage", {}) or {}, finish_reason=None, raw=data)

    def call(self, model: str, user_text: str, **kwargs: Any) -> LLMResponse:
        
        """
        외부에서 호출하는 단일 진입점

        흐름:
        1. model → router → path / provider 결정
        2. provider → payload 스키마 생성
        3. HTTP POST 요청
        4. 응답을 LLMResponse로 정규화해서 반환

        의도:
        - 이 함수만 보면 "모델 + 텍스트 → 응답"으로 보이게 만들기
        - 내부 복잡성(path, payload 차이)은 전부 숨김
        """

        path, provider = self.router(model)
        url = f"{self.base_url}/{path.lstrip('/')}"
        payload = self.build_payload(model, user_text, **kwargs)

        response = requests.post(url, headers=self._headers(), json=payload, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        return self._parse_result(provider, data)