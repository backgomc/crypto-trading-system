#!/usr/bin/env python3
"""
VS Code Server 호환성 진단 스크립트
나스 환경에서 VS Code Remote SSH 연결 문제 진단용
"""

import os
import subprocess
import platform
import sys
from pathlib import Path

def run_command(command):
    """명령어 실행 및 결과 반환"""
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=10)
        return result.returncode == 0, result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        return False, "", "명령어 실행 시간 초과"
    except Exception as e:
        return False, "", str(e)

def check_file_exists(filepath):
    """파일 존재 여부 확인"""
    return Path(filepath).exists()

def print_header(title):
    """섹션 헤더 출력"""
    print(f"\n{'='*50}")
    print(f"🔍 {title}")
    print('='*50)

def print_result(item, status, details=""):
    """결과 출력 (체크마크와 함께)"""
    icon = "✅" if status else "❌"
    print(f"{icon} {item}")
    if details:
        print(f"   → {details}")

def diagnose_system_info():
    """시스템 정보 진단"""
    print_header("시스템 정보")
    
    # 기본 시스템 정보
    print(f"🖥️  운영체제: {platform.system()}")
    print(f"🏷️  배포판: {platform.platform()}")
    print(f"⚙️  아키텍처: {platform.machine()}")
    print(f"🐍 Python: {platform.python_version()}")
    
    # uname 정보
    success, output, _ = run_command("uname -a")
    if success:
        print(f"📋 상세 정보: {output}")

def diagnose_c_library():
    """C 라이브러리 타입 진단"""
    print_header("C 라이브러리 타입 확인")
    
    # musl libc 확인 (Alpine Linux)
    musl_path = "/lib/ld-musl-x86_64.so.1"
    musl_exists = check_file_exists(musl_path)
    print_result("musl libc (Alpine Linux)", musl_exists, musl_path if musl_exists else "없음")
    
    # glibc 확인 (Ubuntu/Debian/CentOS)
    glibc_paths = [
        "/lib/x86_64-linux-gnu/ld-linux-x86-64.so.2",
        "/lib64/ld-linux-x86-64.so.2",
        "/lib/ld-linux-x86-64.so.2"
    ]
    
    glibc_found = False
    for path in glibc_paths:
        if check_file_exists(path):
            print_result("glibc (Ubuntu/Debian/CentOS)", True, path)
            glibc_found = True
            break
    
    if not glibc_found:
        print_result("glibc (Ubuntu/Debian/CentOS)", False, "표준 경로에서 찾을 수 없음")
    
    # 라이브러리 타입 요약
    if musl_exists:
        print("\n🎯 결론: Alpine Linux (musl) 환경")
    elif glibc_found:
        print("\n🎯 결론: 표준 Linux (glibc) 환경")
    else:
        print("\n⚠️  경고: 알 수 없는 C 라이브러리 환경")

def diagnose_essential_libraries():
    """필수 라이브러리 확인"""
    print_header("VS Code Server 필수 라이브러리")
    
    essential_libs = [
        "/lib/ld-musl-x86_64.so.1",  # Alpine musl
        "/lib/x86_64-linux-gnu/ld-linux-x86-64.so.2",  # Ubuntu/Debian glibc
        "/lib64/ld-linux-x86-64.so.2",  # CentOS/RHEL glibc
        "/usr/lib/x86_64-linux-gnu/libstdc++.so.6",  # libstdc++
        "/usr/lib/libstdc++.so.6",
        "/lib/x86_64-linux-gnu/libstdc++.so.6"
    ]
    
    found_libs = []
    for lib in essential_libs:
        exists = check_file_exists(lib)
        if exists:
            found_libs.append(lib)
            print_result(f"라이브러리: {lib}", True)
    
    if not found_libs:
        print_result("필수 라이브러리", False, "핵심 라이브러리를 찾을 수 없음")
    
    # find 명령어로 추가 검색
    print("\n🔍 시스템 전체 라이브러리 검색:")
    search_commands = [
        'find /lib /usr/lib -name "*ld-musl*" 2>/dev/null',
        'find /lib /usr/lib -name "*libstdc++*" 2>/dev/null | head -3',
        'find /lib* /usr/lib* -name "*libc.so*" 2>/dev/null | head -3'
    ]
    
    for cmd in search_commands:
        success, output, _ = run_command(cmd)
        if success and output:
            print(f"   {output}")

def diagnose_nodejs():
    """Node.js 호환성 확인"""
    print_header("Node.js 호환성")
    
    # Node.js 설치 확인
    success, output, _ = run_command("which node")
    if success:
        version_success, version, _ = run_command("node --version")
        if version_success:
            print_result("Node.js 설치", True, f"경로: {output}, 버전: {version}")
        else:
            print_result("Node.js 설치", True, f"경로: {output}, 버전 확인 실패")
    else:
        print_result("Node.js 설치", False, "Node.js를 찾을 수 없음")
    
    # npm 확인
    success, output, _ = run_command("which npm")
    if success:
        print_result("npm 설치", True, output)
    else:
        print_result("npm 설치", False, "npm을 찾을 수 없음")

def diagnose_dynamic_linker():
    """동적 링커 정보 확인"""
    print_header("동적 링커 정보")
    
    # ldd 버전 확인
    success, output, _ = run_command("ldd --version")
    if success:
        print_result("ldd 사용 가능", True, output.split('\n')[0])
    else:
        print_result("ldd 사용 가능", False, "ldd 명령어 없음")
    
    # 동적 링커 파일들 확인
    linker_paths = ["/lib*/ld*", "/lib64/ld*"]
    success, output, _ = run_command("ls -la /lib*/ld* /lib64/ld* 2>/dev/null")
    if success and output:
        print("📁 동적 링커 파일들:")
        for line in output.split('\n')[:5]:  # 처음 5개만 표시
            print(f"   {line}")

def diagnose_package_manager():
    """패키지 관리자 및 설치된 패키지 확인"""
    print_header("패키지 관리자 및 라이브러리 패키지")
    
    # 각 패키지 관리자별 확인
    package_managers = [
        ("apk", "apk info | grep -E '(glibc|libstdc|musl)' 2>/dev/null"),
        ("apt", "dpkg -l | grep -E '(libc6|libstdc)' 2>/dev/null"),
        ("yum", "rpm -qa | grep -E '(glibc|libstdc)' 2>/dev/null"),
        ("dnf", "dnf list installed | grep -E '(glibc|libstdc)' 2>/dev/null")
    ]
    
    for pm_name, cmd in package_managers:
        # 패키지 관리자 존재 확인
        success, _, _ = run_command(f"which {pm_name}")
        if success:
            print_result(f"{pm_name} 패키지 관리자", True)
            
            # 관련 패키지 검색
            success, output, _ = run_command(cmd)
            if success and output:
                print(f"   📦 설치된 관련 패키지:")
                for line in output.split('\n')[:3]:  # 처음 3개만 표시
                    print(f"      {line}")
        else:
            print_result(f"{pm_name} 패키지 관리자", False)

def generate_recommendations():
    """해결 방안 추천"""
    print_header("해결 방안 추천")
    
    # musl vs glibc 확인
    has_musl = check_file_exists("/lib/ld-musl-x86_64.so.1")
    has_glibc = any(check_file_exists(p) for p in [
        "/lib/x86_64-linux-gnu/ld-linux-x86-64.so.2",
        "/lib64/ld-linux-x86-64.so.2"
    ])
    
    if has_musl:
        print("🎯 Alpine Linux (musl) 환경 감지됨")
        print("   💡 추천 해결책:")
        print("   1. sudo apk add libstdc++ glibc")
        print("   2. sudo apk add gcompat  # glibc 호환 레이어")
        print("   3. Docker 컨테이너 직접 접속 방식 사용")
        
    elif has_glibc:
        print("🎯 표준 Linux (glibc) 환경 감지됨")
        print("   💡 추천 해결책:")
        print("   1. sudo apt-get install libc6 libstdc++6  # Ubuntu/Debian")
        print("   2. sudo yum install glibc libstdc++  # CentOS/RHEL")
        
    else:
        print("⚠️  알 수 없는 환경")
        print("   💡 추천 해결책:")
        print("   1. SFTP 확장으로 파일 동기화")
        print("   2. Docker 컨테이너 직접 접속")
        print("   3. 포트 포워딩으로 웹 기반 VS Code 사용")
    
    print("\n🔧 추가 해결 방법:")
    print("   • VS Code Server 수동 재설치")
    print("   • Remote-Containers 확장 사용")
    print("   • 웹 기반 코드 에디터 (code-server) 설치")

def main():
    """메인 진단 함수"""
    print("🚀 VS Code Server 호환성 진단 시작!")
    print(f"📅 실행 시간: {subprocess.run(['date'], capture_output=True, text=True).stdout.strip()}")
    
    try:
        diagnose_system_info()
        diagnose_c_library()
        diagnose_essential_libraries()
        diagnose_nodejs()
        diagnose_dynamic_linker()
        diagnose_package_manager()
        generate_recommendations()
        
        print_header("진단 완료")
        print("✅ 진단이 완료되었습니다!")
        print("📋 위 결과를 참고하여 적절한 해결책을 적용해보세요.")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  사용자에 의해 진단이 중단되었습니다.")
    except Exception as e:
        print(f"\n\n❌ 진단 중 오류 발생: {e}")

if __name__ == "__main__":
    main()
