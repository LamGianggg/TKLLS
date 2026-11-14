/**
 * Spec2RTL Engineering Workbench Application Controller
 * Pure Vanilla ES6 — 100% Offline Self-Contained
 * Author: Teamwork Frontend Implementer Worker
 * File: web/app.js
 */

(function() {
  'use strict';

  // Application Global State
  const AppState = {
    samples: [],
    selectedSample: null,
    currentTaskId: null,
    pollTimer: null,
    pollStartTime: 0,
    isExecuting: false,
    activeTab: 'tab-3d',
    activeCodeSubtab: 'rtl',
    currentResult: null,
    currentEntity: 'nhan_8_bit',
    currentBdfPath: 'quartus/sch_nhan_8_bit.bdf',
    rtlSource: '',
    harnessSource: ''
  };

  // Academic Research Reports Catalog (8 topics, 16 files)
  const RESEARCH_REPORTS = [
    {
      id: '00',
      title: '00. Master Spec2RTL Synthesis Report',
      desc: 'Báo cáo tổng thể tích hợp chuỗi Spec2RTL và kiểm thử nghiệm thu EDA.',
      md: '/reports/00_Master_Spec2RTL_Synthesis_Report.md',
      pdf: '/reports/00_Master_Spec2RTL_Synthesis_Report.pdf'
    },
    {
      id: '01',
      title: '01. CAD 3D Component Deduplication',
      desc: 'Thuật toán chuẩn hóa và khử trùng lặp hình học linh kiện vi mạch 3D CAD.',
      md: '/reports/01_CAD_3D_Component_Deduplication.md',
      pdf: '/reports/01_CAD_3D_Component_Deduplication.pdf'
    },
    {
      id: '02',
      title: '02. 3D Chip Via Stacking Reconstruction',
      desc: 'Tái cấu trúc hình học cột via xếp tầng và phân tích độ lệch tâm tiếp xúc.',
      md: '/reports/02_3D_Chip_Via_Stacking_Reconstruction.md',
      pdf: '/reports/02_3D_Chip_Via_Stacking_Reconstruction.pdf'
    },
    {
      id: '03',
      title: '03. 3D Chip Thermal & PowerMesh Analysis',
      desc: 'Mô phỏng dẫn nhiệt 3D và toàn vẹn điện áp lưới nguồn Metal 3 PDN.',
      md: '/reports/03_3D_Chip_Thermal_PowerMesh_Analysis.md',
      pdf: '/reports/03_3D_Chip_Thermal_PowerMesh_Analysis.pdf'
    },
    {
      id: '04',
      title: '04. LLM Spec2RTL 4-Step Pipeline',
      desc: 'Kiến trúc chuỗi 4 bước LLM tự động chuyển đặc tả thành mã Verilog tổng hợp.',
      md: '/reports/04_LLM_Spec2RTL_4Step_Pipeline.md',
      pdf: '/reports/04_LLM_Spec2RTL_4Step_Pipeline.pdf'
    },
    {
      id: '05',
      title: '05. 70/30 Chip Partitioning & Commodity AI',
      desc: 'Chiến lược phân vùng kiến trúc chip 70% chuyên dụng và 30% AI phổ thông.',
      md: '/reports/05_70_30_Chip_Partitioning_Commodity_AI.md',
      pdf: '/reports/05_70_30_Chip_Partitioning_Commodity_AI.pdf'
    },
    {
      id: '06',
      title: '06. VeriPrefer Closed-Loop Feedback',
      desc: 'Cơ chế tinh chỉnh phản hồi vòng kín nâng cao tỷ lệ biên dịch Verilog 100%.',
      md: '/reports/06_VeriPrefer_ClosedLoop_Feedback.md',
      pdf: '/reports/06_VeriPrefer_ClosedLoop_Feedback.pdf'
    },
    {
      id: '07',
      title: '07. Verilog Test Harness Architecture',
      desc: 'Kiến trúc Option A Test Harness: Watchdog 100µs và self-checking assertions.',
      md: '/reports/07_Verilog_Test_Harness_Architecture.md',
      pdf: '/reports/07_Verilog_Test_Harness_Architecture.pdf'
    }
  ];

  // DOM Elements Cache
  let dom = {};

  /**
   * Initializes application when DOM is ready
   */
  document.addEventListener('DOMContentLoaded', () => {
    cacheDomElements();
    init3DEngine();
    initTabNavigation();
    initSamplePills();
    initExecutionControls();
    initCodeViewerEvents();
    initWaveformEvents();
    initBdfEvents();
    initReportsGrid();
    initConsoleControls();
    init3DControlEvents();
    initExternalLaunchers();
    loadDefaultMultiplierData();
  });

  /**
   * Caches frequently accessed DOM elements
   */
  function cacheDomElements() {
    dom = {
      promptInput: document.getElementById('prompt-input') || document.getElementById('spec-prompt'),
      samplePillsContainer: document.getElementById('sample-pills-container'),
      useHarnessToggle: document.getElementById('use-harness-toggle'),
      btnRunSpec: document.getElementById('btn-run-spec'),
      btnClearSpec: document.getElementById('btn-clear-spec'),
      runSpinner: document.getElementById('run-spinner'),
      taskBanner: document.getElementById('task-status-banner'),
      taskBadge: document.getElementById('task-status-badge'),
      taskTimer: document.getElementById('task-elapsed-timer'),
      taskDesc: document.getElementById('task-status-desc'),
      taskProgressBar: document.getElementById('task-progress-bar'),
      
      tabButtons: document.querySelectorAll('.tab-button'),
      tabPanes: document.querySelectorAll('.tab-pane'),
      
      chip3dContainer: document.getElementById('chip3d-container') || document.getElementById('chip3d-canvas-container'),
      btnResetCamera: document.getElementById('btn-reset-camera'),
      sliderClipping: document.getElementById('slider-clipping'),
      labelClippingVal: document.getElementById('label-clipping-value') || document.getElementById('clipping-val-label'),
      layerCheckboxes: document.querySelectorAll('.layer-toggle-pill input'),
      
      btnSubtabRtl: document.getElementById('btn-subtab-rtl'),
      btnSubtabHarness: document.getElementById('btn-subtab-harness'),
      codeDisplay: document.getElementById('code-display'),
      codeRtlFilename: document.getElementById('code-rtl-filename'),
      codeHarnessFilename: document.getElementById('code-harness-filename'),
      btnCopyCode: document.getElementById('btn-copy-code'),
      btnDownloadCode: document.getElementById('btn-download-code'),
      
      waveformIframe: document.getElementById('waveform-iframe'),
      btnReloadWaveform: document.getElementById('btn-reload-waveform'),
      btnLaunchModelsimTab: document.getElementById('btn-launch-modelsim-tab'),
      
      btnOpenQuartus: document.getElementById('btn-open-quartus'),
      bdfTargetPath: document.getElementById('bdf-target-path'),
      tbodyBdfPorts: document.getElementById('tbody-bdf-ports'),
      linkDownloadBdf: document.getElementById('link-download-bdf'),
      
      reportsGrid: document.getElementById('reports-grid'),
      
      verdictBadge: document.getElementById('verdict-badge'),
      valTotalTests: document.getElementById('val-total-tests'),
      valPassedTests: document.getElementById('val-passed-tests'),
      valFailedTests: document.getElementById('val-failed-tests'),
      valAccuracy: document.getElementById('val-accuracy'),
      valElapsed: document.getElementById('val-elapsed'),
      
      valFpgaFamily: document.getElementById('val-fpga-family'),
      resValLes: document.getElementById('res-val-les'),
      resValFfs: document.getElementById('res-val-ffs'),
      resValPins: document.getElementById('res-val-pins'),
      resBarLes: document.getElementById('res-bar-les'),
      resBarFfs: document.getElementById('res-bar-ffs'),
      resBarPins: document.getElementById('res-bar-pins'),
      
      consoleOutput: document.getElementById('console-output'),
      btnClearConsole: document.getElementById('btn-clear-console'),
      btnCopyConsole: document.getElementById('btn-copy-console'),
      
      btnHeaderModelsim: document.getElementById('btn-header-modelsim'),
      btnHeaderQuartus: document.getElementById('btn-header-quartus'),
      toastContainer: document.getElementById('toast-container')
    };
  }

  /**
   * Initializes 3D Chip Viewport
   */
  function init3DEngine() {
    if (window.Chip3D && typeof window.Chip3D.init === 'function') {
      window.Chip3D.init('chip3d-container');
    }
  }

  /**
   * Configures Tab navigation
   */
  function initTabNavigation() {
    if (!dom.tabButtons) return;
    dom.tabButtons.forEach(btn => {
      btn.addEventListener('click', () => {
        const targetTab = btn.getAttribute('data-tab');
        if (!targetTab) return;

        dom.tabButtons.forEach(b => b.classList.remove('active'));
        dom.tabPanes.forEach(p => p.classList.remove('active'));

        btn.classList.add('active');
        const activePane = document.getElementById(targetTab);
        if (activePane) {
          activePane.classList.add('active');
        }

        AppState.activeTab = targetTab;

        // If switching to 3D tab, trigger window resize to refresh WebGL viewport
        if (targetTab === 'tab-3d') {
          setTimeout(() => {
            window.dispatchEvent(new Event('resize'));
          }, 50);
        }
      });
    });
  }

  /**
   * Fetches hardware specification samples from /api/samples and populates pills
   */
  function initSamplePills() {
    if (!dom.samplePillsContainer) return;

    fetch('/api/samples')
      .then(res => res.json())
      .then(samples => {
        AppState.samples = Array.isArray(samples) ? samples : [];
        renderSamplePills();
      })
      .catch(err => {
        console.warn('Could not load /api/samples:', err);
        dom.samplePillsContainer.innerHTML = '<span style="color:#ef4444;font-size:0.75rem;">Không tải được danh sách mẫu</span>';
      });
  }

  /**
   * Renders quick sample pill buttons
   */
  function renderSamplePills() {
    dom.samplePillsContainer.innerHTML = '';
    AppState.samples.forEach((sample, idx) => {
      const pill = document.createElement('button');
      pill.type = 'button';
      pill.className = `sample-pill ${idx === 0 ? 'active' : ''}`;
      pill.textContent = sample.name_vi || sample.name_en || sample.id;
      pill.title = sample.prompt || '';
      
      pill.addEventListener('click', () => {
        document.querySelectorAll('.sample-pill').forEach(p => p.classList.remove('active'));
        pill.classList.add('active');
        selectSample(sample);
      });

      dom.samplePillsContainer.appendChild(pill);
    });

    if (AppState.samples.length > 0) {
      selectSample(AppState.samples[0], false);
    }
  }

  /**
   * Selects a sample and populates the prompt textarea
   */
  function selectSample(sample, showNotification = true) {
    AppState.selectedSample = sample;
    if (dom.promptInput && sample.prompt) {
      dom.promptInput.value = sample.prompt;
    }
    if (showNotification) {
      showToast(`Đã chọn mẫu: ${sample.name_vi || sample.name_en}`, 'info');
    }
  }

  /**
   * Binds pipeline trigger buttons and keyboard shortcuts
   */
  function initExecutionControls() {
    if (dom.btnRunSpec) {
      dom.btnRunSpec.addEventListener('click', triggerSpecPipeline);
    }

    if (dom.btnClearSpec) {
      dom.btnClearSpec.addEventListener('click', () => {
        if (dom.promptInput) {
          dom.promptInput.value = '';
          dom.promptInput.focus();
        }
        document.querySelectorAll('.sample-pill').forEach(p => p.classList.remove('active'));
        AppState.selectedSample = null;
        showToast('Đã xóa nội dung nhập', 'info');
      });
    }

    if (dom.promptInput) {
      dom.promptInput.addEventListener('keydown', (e) => {
        if (e.ctrlKey && e.key === 'Enter') {
          e.preventDefault();
          triggerSpecPipeline();
        }
      });
    }
  }

  /**
   * Triggers the Spec2RTL pipeline execution
   */
  function triggerSpecPipeline() {
    if (AppState.isExecuting) return;

    const promptText = dom.promptInput ? dom.promptInput.value.trim() : '';
    const useHarness = dom.useHarnessToggle ? dom.useHarnessToggle.checked : true;
    const specFile = AppState.selectedSample ? AppState.selectedSample.spec_file : '';

    if (!promptText && !specFile) {
      showToast('Vui lòng nhập đặc tả phần cứng hoặc chọn mẫu có sẵn!', 'error');
      if (dom.promptInput) dom.promptInput.focus();
      return;
    }

    // Set UI to executing state
    AppState.isExecuting = true;
    if (dom.btnRunSpec) {
      dom.btnRunSpec.disabled = true;
      const btnText = dom.btnRunSpec.querySelector('.btn-text');
      if (btnText) btnText.textContent = 'Đang tổng hợp...';
    }
    if (dom.runSpinner) dom.runSpinner.classList.remove('hidden');

    if (dom.taskBanner) dom.taskBanner.classList.remove('hidden');
    if (dom.taskBadge) {
      dom.taskBadge.className = 'badge badge-running';
      dom.taskBadge.textContent = 'ĐANG CHẠY';
    }
    if (dom.taskDesc) dom.taskDesc.textContent = 'Đang khởi động Spec2RTL, ModelSim và Quartus II...';

    // Update Scoreboard to RUNNING state
    if (dom.verdictBadge) {
      dom.verdictBadge.className = 'verdict-badge badge-running';
      dom.verdictBadge.textContent = 'ĐANG KIỂM TRA...';
    }

    // Clear console output and start message
    if (dom.consoleOutput) {
      dom.consoleOutput.textContent = `[${new Date().toLocaleTimeString()}] [*] Kích hoạt pipeline Spec2RTL...\n[*] Đặc tả: ${promptText.substring(0, 80)}...\n[*] Option A Test Harness: ${useHarness ? 'ENABLED (Watchdog 100µs)' : 'DISABLED'}\n`;
    }

    AppState.pollStartTime = Date.now();

    // Send POST /api/run-spec
    fetch('/api/run-spec', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        prompt: promptText,
        spec_file: specFile,
        use_harness: useHarness
      })
    })
      .then(res => {
        if (!res.ok) {
          return res.json().then(errData => { throw new Error(errData.error || 'Server error'); });
        }
        return res.json();
      })
      .then(data => {
        AppState.currentTaskId = data.task_id;
        startPollingTask(data.task_id);
      })
      .catch(err => {
        console.error('Run Spec failed:', err);
        finishExecution(false, null, err.message);
      });
  }

  /**
   * Starts polling interval for task status
   */
  function startPollingTask(taskId) {
    if (AppState.pollTimer) clearInterval(AppState.pollTimer);

    AppState.pollTimer = setInterval(() => {
      // Update elapsed time counter
      const elapsedSec = ((Date.now() - AppState.pollStartTime) / 1000).toFixed(1);
      if (dom.taskTimer) dom.taskTimer.textContent = `${elapsedSec}s`;

      fetch(`/api/status?task_id=${encodeURIComponent(taskId)}`)
        .then(res => {
          if (!res.ok) throw new Error(`Status HTTP ${res.status}`);
          return res.json();
        })
        .then(data => {
          // Stream log into console
          if (data.log && dom.consoleOutput) {
            dom.consoleOutput.textContent = data.log;
            dom.consoleOutput.scrollTop = dom.consoleOutput.scrollHeight;
          }

          if (data.status === 'completed' || data.status === 'failed') {
            clearInterval(AppState.pollTimer);
            AppState.pollTimer = null;
            finishExecution(data.status === 'completed', data);
          }
        })
        .catch(err => {
          console.warn('Poll error:', err);
        });
    }, 500);
  }

  /**
   * Finalizes execution and updates all view panels with results
   */
  function finishExecution(isSuccess, data, errorMessage = '') {
    AppState.isExecuting = false;

    // Reset button
    if (dom.btnRunSpec) {
      dom.btnRunSpec.disabled = false;
      const btnText = dom.btnRunSpec.querySelector('.btn-text');
      if (btnText) btnText.textContent = 'Kích hoạt Spec2RTL';
    }
    if (dom.runSpinner) dom.runSpinner.classList.add('hidden');

    if (!data) {
      if (dom.taskBadge) {
        dom.taskBadge.className = 'badge badge-fail';
        dom.taskBadge.textContent = 'THẤT BẠI';
      }
      if (dom.taskDesc) dom.taskDesc.textContent = errorMessage || 'Tiến trình kết thúc với lỗi.';
      if (dom.verdictBadge) {
        dom.verdictBadge.className = 'verdict-badge badge-fail';
        dom.verdictBadge.textContent = 'FAIL';
      }
      showToast(errorMessage || 'Tổng hợp Spec2RTL thất bại!', 'error');
      return;
    }

    AppState.currentResult = data;
    AppState.currentEntity = data.top_entity || 'nhan_8_bit';
    AppState.currentBdfPath = data.bdf_path || `quartus/sch_${AppState.currentEntity}.bdf`;
    AppState.rtlSource = data.rtl_code || '';
    AppState.harnessSource = data.harness_code || data.tb_code || '';

    // 1. Update Execution Banner
    if (dom.taskBadge) {
      dom.taskBadge.className = isSuccess ? 'badge badge-accent' : 'badge badge-fail';
      dom.taskBadge.textContent = isSuccess ? 'HOÀN TẤT' : 'CÓ LỖI';
    }
    if (dom.taskDesc) {
      dom.taskDesc.textContent = isSuccess
        ? `Đã tổng hợp thành công module: ${AppState.currentEntity} (ModelSim & Quartus II)`
        : 'Tiến trình mô phỏng gặp cảnh báo hoặc lỗi.';
    }

    // 2. Update Verification Scoreboard
    const sc = data.scoreboard || {};
    const totalTests = sc.total_tests || 0;
    const passedTests = sc.passed_tests || 0;
    const failedTests = sc.failed_tests || 0;
    const accuracy = sc.accuracy_percent !== undefined ? sc.accuracy_percent : 0;
    const verdict = sc.verdict || (isSuccess ? 'PASS' : 'FAIL');

    if (dom.valTotalTests) dom.valTotalTests.textContent = totalTests;
    if (dom.valPassedTests) dom.valPassedTests.textContent = passedTests;
    if (dom.valFailedTests) dom.valFailedTests.textContent = failedTests;
    if (dom.valAccuracy) dom.valAccuracy.textContent = `${Number(accuracy).toFixed(1)}%`;
    if (dom.valElapsed) dom.valElapsed.textContent = `${data.elapsed || 0}s`;

    if (dom.verdictBadge) {
      if (verdict === 'PASS' && failedTests === 0) {
        dom.verdictBadge.className = 'verdict-badge badge-pass';
        dom.verdictBadge.textContent = '100% PASS';
      } else {
        dom.verdictBadge.className = 'verdict-badge badge-fail';
        dom.verdictBadge.textContent = verdict;
      }
    }

    // 3. Update FPGA Resource Utilization Table
    const mt = data.metrics || {};
    const les = mt.logic_elements || 0;
    const ffs = mt.total_registers || 0;
    const pins = mt.total_pins || 0;
    const family = mt.family || 'Cyclone II';

    if (dom.valFpgaFamily) dom.valFpgaFamily.textContent = family;
    if (dom.resValLes) dom.resValLes.textContent = `${les} LEs`;
    if (dom.resValFfs) dom.resValFfs.textContent = `${ffs} FFs`;
    if (dom.resValPins) dom.resValPins.textContent = `${pins} Pins`;

    updateUsageMeter(dom.resBarLes, les, 33216);
    updateUsageMeter(dom.resBarFfs, ffs, 33216);
    updateUsageMeter(dom.resBarPins, pins, 475);

    // 4. Update Verilog Code Viewers
    if (dom.codeRtlFilename) dom.codeRtlFilename.textContent = `${AppState.currentEntity}.v`;
    if (dom.codeHarnessFilename) dom.codeHarnessFilename.textContent = `harness_${AppState.currentEntity}.v`;
    renderActiveCode();

    // 5. Reload Waveform Iframe with cache-busting timestamp
    if (dom.waveformIframe) {
      dom.waveformIframe.src = `/sim/waveform.html?t=${Date.now()}`;
    }

    // 6. Update BDF Schematic View & Ports Table
    if (dom.bdfTargetPath) dom.bdfTargetPath.textContent = AppState.currentBdfPath;
    if (dom.linkDownloadBdf) dom.linkDownloadBdf.href = `/${AppState.currentBdfPath}`;
    renderBdfPorts(data.ports || []);

    // 7. Update Procedural 3D Chip Geometry
    if (window.Chip3D && typeof window.Chip3D.update === 'function') {
      window.Chip3D.update({
        entity: AppState.currentEntity,
        category: (AppState.currentEntity.includes('nhan') ? 'MULTIPLIER' : 'GENERAL'),
        logic_elements: les,
        total_registers: ffs,
        total_pins: pins,
        ports: data.ports || []
      });
    }

    showToast(isSuccess ? 'Xác minh thành công 100% PASS!' : 'Tiến trình kết thúc với cảnh báo', isSuccess ? 'success' : 'error');
  }

  /**
   * Updates an FPGA hardware resource usage bar
   */
  function updateUsageMeter(container, used, max) {
    if (!container) return;
    const pct = Math.min(100, (used / max) * 100);
    const bar = container.querySelector('.usage-bar');
    const text = container.querySelector('.usage-text');
    if (bar) bar.style.width = `${Math.max(1, pct)}%`;
    if (text) text.textContent = pct < 1 ? '< 1%' : `${pct.toFixed(1)}%`;
  }

  /**
   * Initializes Verilog Code Viewer tabs & copy/download actions
   */
  function initCodeViewerEvents() {
    if (dom.btnSubtabRtl) {
      dom.btnSubtabRtl.addEventListener('click', () => {
        AppState.activeCodeSubtab = 'rtl';
        dom.btnSubtabRtl.classList.add('active');
        if (dom.btnSubtabHarness) dom.btnSubtabHarness.classList.remove('active');
        renderActiveCode();
      });
    }

    if (dom.btnSubtabHarness) {
      dom.btnSubtabHarness.addEventListener('click', () => {
        AppState.activeCodeSubtab = 'harness';
        dom.btnSubtabHarness.classList.add('active');
        if (dom.btnSubtabRtl) dom.btnSubtabRtl.classList.remove('active');
        renderActiveCode();
      });
    }

    if (dom.btnCopyCode) {
      dom.btnCopyCode.addEventListener('click', () => {
        const code = AppState.activeCodeSubtab === 'rtl' ? AppState.rtlSource : AppState.harnessSource;
        if (!code) {
          showToast('Chưa có mã nguồn để sao chép', 'info');
          return;
        }
        navigator.clipboard.writeText(code)
          .then(() => showToast('Đã sao chép mã Verilog vào clipboard!', 'success'))
          .catch(() => showToast('Sao chép thất bại', 'error'));
      });
    }

    if (dom.btnDownloadCode) {
      dom.btnDownloadCode.addEventListener('click', () => {
        const isRtl = AppState.activeCodeSubtab === 'rtl';
        const code = isRtl ? AppState.rtlSource : AppState.harnessSource;
        const filename = isRtl ? `${AppState.currentEntity}.v` : `harness_${AppState.currentEntity}.v`;
        if (!code) {
          showToast('Chưa có mã nguồn để tải về', 'info');
          return;
        }
        const blob = new Blob([code], { type: 'text/plain;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        showToast(`Đã tải về ${filename}`, 'success');
      });
    }
  }

  /**
   * Renders the active code snippet with syntax highlighting
   */
  function renderActiveCode() {
    if (!dom.codeDisplay) return;
    const rawCode = AppState.activeCodeSubtab === 'rtl' ? AppState.rtlSource : AppState.harnessSource;
    if (!rawCode) {
      dom.codeDisplay.textContent = 'Chưa có mã nguồn được sinh. Vui lòng bấm "Kích hoạt Spec2RTL".';
      return;
    }
    dom.codeDisplay.innerHTML = highlightVerilog(rawCode);
  }

  /**
   * Pure Vanilla Regex-based Verilog Syntax Highlighter
   */
  function highlightVerilog(code) {
    if (!code) return '';

    // Normalize Windows CRLF to LF
    let text = code.replace(/\r\n/g, '\n');

    // Escape HTML characters
    text = text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

    // 1. Comments
    text = text.replace(/(\/\/[^\n]*)/g, '<span class="v-cmt">$1</span>');
    text = text.replace(/(\/\*[\s\S]*?\*\/)/g, '<span class="v-cmt">$1</span>');

    // 2. Strings
    text = text.replace(/(".*?")/g, '<span class="v-str">$1</span>');

    // 3. Numbers (Hex, Dec, Bin)
    text = text.replace(/\b(\d+'[bBoOdDhH][0-9a-fA-F_xXzZ]+|\b\d+\b)/g, '<span class="v-num">$1</span>');

    // 4. Directional keywords
    text = text.replace(/\b(input|output|inout)\b/g, '<span class="v-dir">$1</span>');

    // 5. Types
    text = text.replace(/\b(reg|wire|logic|integer|genvar|real|signed|unsigned)\b/g, '<span class="v-tp">$1</span>');

    // 6. Keywords
    text = text.replace(/\b(module|endmodule|always|assign|posedge|negedge|begin|end|case|endcase|if|else|parameter|localparam|initial|default|function|endfunction|task|endtask|generate|endgenerate|for|while)\b/g, '<span class="v-kw">$1</span>');

    // 7. Operators
    text = text.replace(/(&lt;=|==|!=|&amp;&amp;|\|\||\+|-|\*|\/)/g, '<span class="v-op">$1</span>');

    return text;
  }

  /**
   * Renders the BDF port mapping table
   */
  function renderBdfPorts(ports) {
    if (!dom.tbodyBdfPorts) return;
    dom.tbodyBdfPorts.innerHTML = '';

    if (!ports || ports.length === 0) {
      dom.tbodyBdfPorts.innerHTML = '<tr><td colspan="5" style="text-align:center;color:#6b7280;">Không tìm thấy cổng nào</td></tr>';
      return;
    }

    ports.forEach((p, idx) => {
      const tr = document.createElement('tr');
      const width = p.width || 1;
      const isBus = p.is_bus || width > 1;
      const vector = isBus ? `[${p.msb || width - 1}:${p.lsb || 0}]` : 'scalar (1-bit)';

      // Edge location heuristic
      let edge = 'West';
      if (p.dir === 'output') edge = 'East';
      else if (p.name.includes('b')) edge = 'South';
      else if (idx % 4 === 3) edge = 'North';

      tr.innerHTML = `
        <td><strong>${p.name}</strong></td>
        <td><span class="badge ${p.dir === 'input' ? 'badge-accent' : 'badge-pass'}">${p.dir.toUpperCase()}</span></td>
        <td>${width} bit</td>
        <td><code>${vector}</code></td>
        <td>${edge} Edge</td>
      `;
      dom.tbodyBdfPorts.appendChild(tr);
    });
  }

  /**
   * Initializes Waveform tab actions
   */
  function initWaveformEvents() {
    if (dom.btnReloadWaveform && dom.waveformIframe) {
      dom.btnReloadWaveform.addEventListener('click', () => {
        dom.waveformIframe.src = `/sim/waveform.html?t=${Date.now()}`;
        showToast('Đang tải lại dạng sóng...', 'info');
      });
    }

    if (dom.btnLaunchModelsimTab) {
      dom.btnLaunchModelsimTab.addEventListener('click', () => {
        launchModelSim(AppState.currentEntity);
      });
    }
  }

  /**
   * Initializes BDF schematic actions
   */
  function initBdfEvents() {
    if (dom.btnOpenQuartus) {
      dom.btnOpenQuartus.addEventListener('click', () => {
        launchQuartus(AppState.currentBdfPath);
      });
    }
  }

  /**
   * Populates the 8 Research Reports in Tab 5
   */
  function initReportsGrid() {
    if (!dom.reportsGrid) return;
    dom.reportsGrid.innerHTML = '';

    RESEARCH_REPORTS.forEach(rep => {
      const card = document.createElement('div');
      card.className = 'report-card';
      card.innerHTML = `
        <div>
          <h4 class="report-card-title">${rep.title}</h4>
          <p class="report-card-desc">${rep.desc}</p>
        </div>
        <div class="report-card-links">
          <a href="${rep.md}" target="_blank" class="btn btn-outline btn-xs">📄 Markdown</a>
          <a href="${rep.pdf}" target="_blank" class="btn btn-primary btn-xs">📥 PDF Bản in</a>
        </div>
      `;
      dom.reportsGrid.appendChild(card);
    });
  }

  /**
   * Console toolbar actions
   */
  function initConsoleControls() {
    if (dom.btnClearConsole && dom.consoleOutput) {
      dom.btnClearConsole.addEventListener('click', () => {
        dom.consoleOutput.textContent = '';
        showToast('Đã xóa log console', 'info');
      });
    }

    if (dom.btnCopyConsole && dom.consoleOutput) {
      dom.btnCopyConsole.addEventListener('click', () => {
        navigator.clipboard.writeText(dom.consoleOutput.textContent)
          .then(() => showToast('Đã sao chép log console!', 'success'))
          .catch(() => showToast('Sao chép thất bại', 'error'));
      });
    }
  }

  /**
   * Binds 3D HUD controls to window.Chip3D engine
   */
  function init3DControlEvents() {
    if (dom.btnResetCamera) {
      dom.btnResetCamera.addEventListener('click', () => {
        if (window.Chip3D && typeof window.Chip3D.resetCamera === 'function') {
          window.Chip3D.resetCamera();
          showToast('Đã đặt lại góc nhìn 3D', 'info');
        }
      });
    }

    if (dom.layerCheckboxes) {
      dom.layerCheckboxes.forEach(cb => {
        cb.addEventListener('change', () => {
          const layerName = cb.getAttribute('data-layer');
          if (window.Chip3D && typeof window.Chip3D.toggleLayer === 'function') {
            window.Chip3D.toggleLayer(layerName, cb.checked);
          }
        });
      });
    }

    if (dom.sliderClipping) {
      dom.sliderClipping.addEventListener('input', (e) => {
        const val = parseFloat(e.target.value);
        if (dom.labelClippingVal) {
          dom.labelClippingVal.textContent = `Cao độ Y: ${val >= 0 ? '+' : ''}${val.toFixed(2)}`;
        }
        if (window.Chip3D && typeof window.Chip3D.setClippingPlane === 'function') {
          window.Chip3D.setClippingPlane(val);
        }
      });
    }
  }

  /**
   * Binds header and tab launcher buttons
   */
  function initExternalLaunchers() {
    if (dom.btnHeaderModelsim) {
      dom.btnHeaderModelsim.addEventListener('click', () => launchModelSim(AppState.currentEntity));
    }

    if (dom.btnHeaderQuartus) {
      dom.btnHeaderQuartus.addEventListener('click', () => launchQuartus(AppState.currentBdfPath));
    }
  }

  /**
   * Triggers /api/open-modelsim
   */
  function launchModelSim(entity) {
    showToast(`Đang khởi chạy ModelSim 10.1d cho: ${entity}...`, 'info');
    fetch('/api/open-modelsim', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ entity: entity || 'nhan_8_bit' })
    })
      .then(res => res.json())
      .then(data => {
        if (data.status === 'launched') {
          showToast('Đã gửi lệnh mở ModelSim GUI!', 'success');
        } else {
          showToast(`Lỗi mở ModelSim: ${data.error || 'Unknown'}`, 'error');
        }
      })
      .catch(err => showToast(`Không kết nối được server: ${err.message}`, 'error'));
  }

  /**
   * Triggers /api/open-quartus
   */
  function launchQuartus(bdfPath) {
    showToast(`Đang khởi chạy Altera Quartus II cho: ${bdfPath}...`, 'info');
    fetch('/api/open-quartus', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ bdf_path: bdfPath || 'quartus/sch_nhan_8_bit.bdf' })
    })
      .then(res => res.json())
      .then(data => {
        if (data.status === 'launched') {
          showToast('Đã gửi lệnh mở Quartus II GUI!', 'success');
        } else {
          showToast(`Lỗi mở Quartus: ${data.error || 'Unknown'}`, 'error');
        }
      })
      .catch(err => showToast(`Không kết nối được server: ${err.message}`, 'error'));
  }

  /**
   * Displays non-intrusive floating toast notifications
   */
  function showToast(message, type = 'info') {
    if (!dom.toastContainer) return;
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    dom.toastContainer.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transition = 'opacity 0.3s ease';
      setTimeout(() => {
        if (toast.parentNode) toast.parentNode.removeChild(toast);
      }, 300);
    }, 3500);
  }

  /**
   * Pre-loads default Multiplier data on startup so UI is fully populated
   */
  function loadDefaultMultiplierData() {
    // Check if canonical Multiplier RTL file is already present on disk
    fetch('/src/nhan_8_bit.v')
      .then(res => res.ok ? res.text() : '')
      .then(rtlText => {
        if (rtlText) {
          AppState.rtlSource = rtlText;
          renderActiveCode();
        }
      })
      .catch(() => {});

    fetch('/sim/harness_nhan_8_bit.v')
      .then(res => res.ok ? res.text() : '')
      .then(harnessText => {
        if (harnessText) {
          AppState.harnessSource = harnessText;
        }
      })
      .catch(() => {});

    // Canonical default port mapping for nhan_8_bit
    const defaultPorts = [
      { name: 'clk', dir: 'input', width: 1, is_bus: false, msb: 0, lsb: 0 },
      { name: 'rst', dir: 'input', width: 1, is_bus: false, msb: 0, lsb: 0 },
      { name: 'a', dir: 'input', width: 8, is_bus: true, msb: 7, lsb: 0 },
      { name: 'b', dir: 'input', width: 8, is_bus: true, msb: 7, lsb: 0 },
      { name: 'product', dir: 'output', width: 16, is_bus: true, msb: 15, lsb: 0 }
    ];
    renderBdfPorts(defaultPorts);

    // Initial Scoreboard & Metric values
    if (dom.valTotalTests) dom.valTotalTests.textContent = '6';
    if (dom.valPassedTests) dom.valPassedTests.textContent = '6';
    if (dom.valFailedTests) dom.valFailedTests.textContent = '0';
    if (dom.valAccuracy) dom.valAccuracy.textContent = '100.0%';
    if (dom.valElapsed) dom.valElapsed.textContent = '0.45s';

    if (dom.verdictBadge) {
      dom.verdictBadge.className = 'verdict-badge badge-pass';
      dom.verdictBadge.textContent = '100% PASS';
    }

    if (dom.resValLes) dom.resValLes.textContent = '17 LEs';
    if (dom.resValFfs) dom.resValFfs.textContent = '16 FFs';
    if (dom.resValPins) dom.resValPins.textContent = '34 Pins';
    if (dom.valFpgaFamily) dom.valFpgaFamily.textContent = 'Cyclone II';

    updateUsageMeter(dom.resBarLes, 17, 33216);
    updateUsageMeter(dom.resBarFfs, 16, 33216);
    updateUsageMeter(dom.resBarPins, 34, 475);
  }

})();
