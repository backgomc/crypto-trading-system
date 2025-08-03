// 파일 경로: web/static/js/dashboard.js
// 코드명: 대시보드 페이지 전용 로직

// ============================================================================
// 전역 변수
// ============================================================================

let tradingViewWidget = null;

// ============================================================================
// TradingView 차트 관리
// ============================================================================

function initTradingView(symbol = "BYBIT:BTCUSDT") {
    const container = document.getElementById('tradingview_chart');
    if (!container) {
        console.error('TradingView 컨테이너를 찾을 수 없습니다.');
        return;
    }
    
    // 기존 위젯 정리
    container.innerHTML = '';
    
    if (typeof TradingView !== 'undefined') {
        try {
            tradingViewWidget = new TradingView.widget({
                width: "100%",
                height: 600,
                symbol: symbol,
                interval: "15",
                timezone: "Asia/Seoul",
                theme: "dark",
                style: "1",
                locale: "kr",
                toolbar_bg: "#1e1e1e",
                enable_publishing: false,
                allow_symbol_change: true,
                container_id: "tradingview_chart",
                
                // 🔧 스키마 오류 해결 설정
                studies: [],
                hide_side_toolbar: false,
                details: false,
                hotlist: false,
                calendar: false,
                mobile_friendly: true,
                auto_scale: true,
                hide_volume: true,
                
                // ⚡ 오류 방지 설정
                disabled_features: [
                    "use_localstorage_for_settings",
                    "volume_force_overlay",
                    "create_volume_indicator_by_default"
                ],
                enabled_features: [
                    "hide_left_toolbar_by_default"
                ],
                
                // 🎯 스키마 검증 우회
                overrides: {
                    "paneProperties.background": "#1e1e1e",
                    "paneProperties.vertGridProperties.color": "#363636",
                    "paneProperties.horzGridProperties.color": "#363636"
                },
                
                // 📊 데이터 설정 개선
                datafeed: undefined,  // 기본 데이터피드 사용
                library_path: undefined,  // CDN 사용
                
                // 🔒 안전 설정
                debug: false,
                custom_css_url: undefined
            });
            
            console.log('✅ TradingView 위젯 초기화 완료');
            
        } catch (error) {
            console.error('❌ TradingView 위젯 생성 오류:', error);
            showChartError();
        }
    } else {
        showChartLoading();
    }
}

function showChartLoading() {
    const container = document.getElementById('tradingview_chart');
    if (container) {
        container.innerHTML = `
            <div class="d-flex justify-content-center align-items-center h-100 chart-placeholder">
                <div class="text-center">
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                    <h5 class="mt-3">차트 로딩 중...</h5>
                    <p>TradingView 차트를 불러오고 있습니다</p>
                </div>
            </div>
        `;
    }
}

function showChartError() {
    const container = document.getElementById('tradingview_chart');
    if (container) {
        container.innerHTML = `
            <div class="d-flex justify-content-center align-items-center h-100 chart-placeholder">
                <div class="text-center">
                    <i class="bi bi-exclamation-triangle text-warning" style="font-size: 3rem;"></i>
                    <h5 class="mt-3">차트 로딩 실패</h5>
                    <p>인터넷 연결을 확인해주세요</p>
                    <button class="btn btn-outline-primary btn-sm" onclick="location.reload()">다시 시도</button>
                </div>
            </div>
        `;
    }
}

function changeSymbol() {
    const selectElement = document.getElementById('chartSymbol');
    const selectedSymbol = selectElement.value;
    showToast('info', `차트를 ${selectedSymbol}로 변경 중...`);
    initTradingView(selectedSymbol);
}

// ============================================================================
// 매매 제어 함수들
// ============================================================================

async function startTrading() {
    if (!confirm('자동매매를 시작하시겠습니까?')) return;
    
    showLoading(true);
    try {
        // TODO: API 연동
        // const result = await apiCall('/api/trading/start', 'POST');
        
        // 임시 시뮬레이션
        await new Promise(resolve => setTimeout(resolve, 1000));
        
        showToast('success', '✅ 자동매매가 시작되었습니다!');
        updateSystemStatus('running');
        
    } catch (error) {
        showToast('error', '❌ 자동매매 시작 실패: ' + error.message);
    } finally {
        showLoading(false);
    }
}

async function stopTrading() {
    if (!confirm('자동매매를 중단하시겠습니까?')) return;
    
    showLoading(true);
    try {
        // TODO: API 연동
        // const result = await apiCall('/api/trading/stop', 'POST');
        
        await new Promise(resolve => setTimeout(resolve, 1000));
        
        showToast('success', '⏹️ 자동매매가 중단되었습니다');
        updateSystemStatus('stopped');
        
    } catch (error) {
        showToast('error', '❌ 자동매매 중단 실패: ' + error.message);
    } finally {
        showLoading(false);
    }
}

async function trainAI() {
    if (!confirm('AI 모델 학습을 시작하시겠습니까?\n학습에는 약 10-30분이 소요됩니다.')) return;
    
    showLoading(true);
    try {
        // TODO: API 연동
        // const result = await apiCall('/api/ai/training/start', 'POST');
        
        await new Promise(resolve => setTimeout(resolve, 2000));
        
        showToast('success', '🧠 AI 학습이 시작되었습니다!');
        updateAIStatus('training');
        
    } catch (error) {
        showToast('error', '❌ AI 학습 시작 실패: ' + error.message);
    } finally {
        showLoading(false);
    }
}

async function emergencyStop() {
    if (!confirm('⚠️ 긴급 청산을 실행하시겠습니까?\n모든 포지션이 즉시 청산됩니다!')) return;
    
    const secondConfirm = prompt('확인을 위해 "긴급청산"을 입력해주세요:');
    if (secondConfirm !== '긴급청산') {
        showToast('warning', '긴급 청산이 취소되었습니다');
        return;
    }
    
    showLoading(true);
    try {
        // TODO: API 연동
        // const result = await apiCall('/api/trading/emergency-stop', 'POST');
        
        await new Promise(resolve => setTimeout(resolve, 1500));
        
        showToast('error', '🚨 긴급 청산이 실행되었습니다!');
        updateSystemStatus('emergency');
        
    } catch (error) {
        showToast('error', '❌ 긴급 청산 실패: ' + error.message);
    } finally {
        showLoading(false);
    }
}

// ============================================================================
// UI 상태 업데이트
// ============================================================================

function updateSystemStatus(status) {
    const statusElements = document.querySelectorAll('.system-status');
    statusElements.forEach(element => {
        const textElement = element.querySelector('h4');
        const iconElement = element.querySelector('.card-icon i');
        
        if (textElement && iconElement) {
            switch (status) {
                case 'running':
                    textElement.textContent = '실행 중';
                    textElement.className = 'text-success';
                    iconElement.className = 'bi bi-play-circle text-success';
                    break;
                case 'stopped':
                    textElement.textContent = '중지됨';
                    textElement.className = 'text-danger';
                    iconElement.className = 'bi bi-stop-circle text-danger';
                    break;
                case 'emergency':
                    textElement.textContent = '긴급 정지';
                    textElement.className = 'text-warning';
                    iconElement.className = 'bi bi-exclamation-triangle text-warning';
                    break;
            }
        }
    });
}

function updateAIStatus(status) {
    const aiStatusElement = document.querySelector('.ai-status-item .badge');
    if (aiStatusElement) {
        switch (status) {
            case 'training':
                aiStatusElement.textContent = '학습 중';
                aiStatusElement.className = 'badge bg-primary';
                break;
            case 'ready':
                aiStatusElement.textContent = '준비됨';
                aiStatusElement.className = 'badge bg-success';
                break;
            case 'error':
                aiStatusElement.textContent = '오류';
                aiStatusElement.className = 'badge bg-danger';
                break;
            default:
                aiStatusElement.textContent = '대기중';
                aiStatusElement.className = 'badge bg-warning';
        }
    }
}

// ============================================================================
// 실시간 데이터 업데이트 (향후 구현)
// ============================================================================

async function loadDashboardData() {
    try {
        // TODO: API 연동
        // const data = await apiCall('/api/dashboard/status');
        
        // 임시 데이터
        const mockData = {
            balance: '10,000,000원',
            todayProfit: '+150,000원',
            profitRate: '+1.5%',
            systemStatus: 'stopped',
            aiAccuracy: '85.3%'
        };
        
        updateDashboardUI(mockData);
        
    } catch (error) {
        console.error('대시보드 데이터 로드 실패:', error);
        showToast('error', '데이터 로드 실패');
    }
}

function updateDashboardUI(data) {
    // UI 업데이트 로직 (향후 구현)
    console.log('대시보드 데이터 업데이트:', data);
}

// ============================================================================
// 페이지 초기화 및 이벤트 리스너
// ============================================================================

function initPageAnimations() {
    const cards = document.querySelectorAll('.status-card, .main-card');
    cards.forEach((card, index) => {
        setTimeout(() => {
            card.style.opacity = '1';
            card.style.transform = 'translateY(0)';
        }, index * 100);
    });
}

function initTradingViewLoader() {
    // TradingView 라이브러리 로드 확인
    const checkTradingView = setInterval(() => {
        if (typeof TradingView !== 'undefined') {
            clearInterval(checkTradingView);
            console.log('✅ TradingView 라이브러리 로드 완료');
            
            if (document.getElementById('tradingview_chart')) {
                initTradingView();
            }
        }
    }, 100);
    
    // 10초 타임아웃
    setTimeout(() => {
        clearInterval(checkTradingView);
        if (typeof TradingView === 'undefined') {
            console.error('❌ TradingView 라이브러리 로드 실패');
            showChartError();
        }
    }, 10000);
}

// ============================================================================
// 페이지 로드 이벤트
// ============================================================================

document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 대시보드 페이지 초기화 시작');
    
    // 페이지 애니메이션
    initPageAnimations();
    
    // 대시보드 데이터 로드
    loadDashboardData();
    
    // 주기적 데이터 업데이트 (5분마다)
    setInterval(loadDashboardData, 5 * 60 * 1000);
    
    console.log('✅ 대시보드 페이지 초기화 완료');
});

window.addEventListener('load', function() {
    // TradingView 초기화
    initTradingViewLoader();
});

// 페이지 언로드 시 정리
window.addEventListener('beforeunload', function() {
    if (tradingViewWidget) {
        tradingViewWidget = null;
    }
});

// ============================================================================
// 전역 함수 노출 (HTML onclick에서 사용)
// ============================================================================

window.changeSymbol = changeSymbol;
window.startTrading = startTrading;
window.stopTrading = stopTrading;
window.trainAI = trainAI;
window.emergencyStop = emergencyStop;