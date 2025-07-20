#!/bin/bash
echo "🚀 암호화폐 자동매매 시스템 코드 자동 푸시 시작..."

# 변경된 파일 목록 확인
echo "📋 변경된 파일 목록:"
git status --porcelain | while read status file; do
  case $status in
    M*) echo "   📝 수정: $file" ;;
    A*) echo "   ➕ 추가: $file" ;;
    D*) echo "   ❌ 삭제: $file" ;;
    R*) echo "   🔄 이름변경: $file" ;;
    ??) echo "   🆕 새파일: $file" ;;
    *) echo "   📄 변경: $file" ;;
  esac
done

# 보안 파일 체크 (.env 파일 등이 실수로 추가되지 않았는지 확인)
echo ""
echo "🔒 보안 파일 체크 중..."
if git status --porcelain | grep -E "\.(env|key|pem)$|secrets\.|config\.py$"; then
    echo "⚠️  경고: 보안 관련 파일이 감지되었습니다!"
    echo "   .env, API 키 파일 등이 포함되어 있지 않은지 확인하세요."
    read -p "   계속 진행하시겠습니까? (y/N): " confirm
    if [[ $confirm != [yY] ]]; then
        echo "❌ 푸시가 취소되었습니다."
        exit 1
    fi
fi

# 현재 시간을 커밋 메시지로 사용
current_time=$(date "+%Y-%m-%d %H:%M:%S")

# 커밋 메시지 입력 옵션
echo ""
read -p "📝 커밋 메시지를 입력하세요 (엔터 시 기본 메시지 사용): " commit_msg

if [ -z "$commit_msg" ]; then
    commit_msg="암호화폐 자동매매 시스템 수정 - $current_time"
fi

# Git 명령어 실행
echo ""
echo "📝 변경사항 추가 중..."
git add .

echo "💾 커밋 생성 중..."
git commit -m "$commit_msg"

echo "📤 GitHub에 푸시 중..."
git push origin main

if [ $? -eq 0 ]; then
    echo "✅ 푸시 완료!"
    echo "🔗 이제 나스에서 업데이트하세요:"
    echo "   ssh nah3207@14.47.172.143"
    echo "   cd /volume2/docker/band_job/crypto-trading-system"
    echo "   git pull"
    echo ""
    echo "🤖 또는 나스에서 deploy.sh 스크립트를 실행하세요!"
else
    echo "❌ 푸시 실패! 오류를 확인해주세요."
    exit 1
fi
