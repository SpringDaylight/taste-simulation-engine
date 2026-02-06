"""
AWS Bedrock 연결 테스트 스크립트
movie_a_2.py의 Bedrock 통합을 테스트합니다.
"""

import os
import json
import boto3
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

def test_bedrock_connection():
    """Bedrock 연결 테스트"""
    print("🚀 AWS Bedrock 연결 테스트 시작\n")
    
    # 환경 변수 확인
    print("=" * 60)
    print("1. 환경 변수 확인")
    print("=" * 60)
    region = os.getenv('AWS_REGION', 'ap-northeast-2')
    access_key = os.getenv('AWS_ACCESS_KEY_ID', '')
    
    print(f"AWS_REGION: {region}")
    print(f"AWS_ACCESS_KEY_ID: {access_key[:10]}...{access_key[-4:] if access_key else 'N/A'}")
    print(f"AWS_SECRET_ACCESS_KEY: {'설정됨' if os.getenv('AWS_SECRET_ACCESS_KEY') else '없음'}\n")
    
    # Bedrock 클라이언트 생성
    print("=" * 60)
    print("2. Bedrock 클라이언트 생성")
    print("=" * 60)
    
    try:
        bedrock_runtime = boto3.client(
            service_name='bedrock-runtime',
            region_name=region,
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
        )
        print("✅ Bedrock 클라이언트 생성 성공\n")
    except Exception as e:
        print(f"❌ Bedrock 클라이언트 생성 실패: {e}\n")
        return False
    
    # Claude 모델 테스트
    print("=" * 60)
    print("3. Claude 모델 테스트")
    print("=" * 60)
    
    try:
        model_id = "anthropic.claude-3-haiku-20240307-v1:0"
        
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 100,
            "messages": [
                {
                    "role": "user",
                    "content": "안녕하세요! 간단히 인사해주세요."
                }
            ],
            "temperature": 0.7
        }
        
        print(f"모델 ID: {model_id}")
        print("Claude 호출 중...")
        
        response = bedrock_runtime.invoke_model(
            modelId=model_id,
            body=json.dumps(request_body)
        )
        
        response_body = json.loads(response['body'].read())
        
        if 'content' in response_body and len(response_body['content']) > 0:
            content_text = response_body['content'][0]['text']
            print(f"✅ Claude 응답 성공!")
            print(f"응답: {content_text}\n")
        else:
            print("❌ Claude 응답 형식 오류\n")
            return False
            
    except Exception as e:
        print(f"❌ Claude 호출 실패: {e}\n")
        return False
    
    # Titan Embedding 테스트
    print("=" * 60)
    print("4. Titan Embedding 테스트")
    print("=" * 60)
    
    try:
        embedding_model_id = "amazon.titan-embed-text-v2:0"
        
        embedding_body = json.dumps({
            "inputText": "감동적인 영화",
            "dimensions": 1024,
            "normalize": True
        })
        
        print(f"모델 ID: {embedding_model_id}")
        print("Titan Embedding 호출 중...")
        
        embedding_response = bedrock_runtime.invoke_model(
            body=embedding_body,
            modelId=embedding_model_id,
            accept="application/json",
            contentType="application/json"
        )
        
        embedding_body = json.loads(embedding_response['body'].read())
        embedding = embedding_body.get('embedding')
        
        if embedding and len(embedding) > 0:
            print(f"✅ Titan Embedding 생성 성공!")
            print(f"  - 벡터 차원: {len(embedding)}")
            print(f"  - 예시 값 (처음 5개): {embedding[:5]}\n")
        else:
            print("❌ Titan Embedding 생성 실패\n")
            return False
            
    except Exception as e:
        print(f"❌ Titan Embedding 호출 실패: {e}\n")
        return False
    
    # 모든 테스트 성공
    print("=" * 60)
    print("📊 테스트 결과 요약")
    print("=" * 60)
    print("✅ 환경 변수       : 정상")
    print("✅ Bedrock 클라이언트 : 정상")
    print("✅ Claude 모델      : 정상")
    print("✅ Titan Embedding  : 정상")
    print("\n🎉 모든 Bedrock 테스트 통과!")
    print("\n다음 단계: python movie_a_2.py --limit 3 --output test_llm.json\n")
    
    return True


if __name__ == '__main__':
    success = test_bedrock_connection()
    exit(0 if success else 1)
