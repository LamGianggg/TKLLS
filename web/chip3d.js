/**
 * Spec2RTL Procedural 3D Chip Visualization Engine
 * Powered by Three.js r128 (100% Offline Bundled)
 * Author: Teamwork Frontend Implementer Worker
 * File: web/chip3d.js
 */
(function(window) {
  'use strict';

  // Core Three.js runtime state
  let scene = null;
  let camera = null;
  let renderer = null;
  let controls = null;
  let containerEl = null;
  let animFrameId = null;
  let clipPlane = null;
  let currentDieDimension = 43.38;

  // 8 Dedicated Layer Groups matching project specification
  const groups = {
    substrate: null,
    cells: null,
    m1: null,
    m2: null,
    m3: null,
    vias: null,
    pads: null,
    labels: null
  };

  /**
   * Authoritative Die Dimension Formula (tests/test_e2e_suite.py)
   * Formula: D = max(24.0, sqrt(LEs + FFs) * 4.0 + Pins * 0.6)
   */
  function calcDieDimension(le, ff, pins) {
    const totalLE = Math.max(0, Number(le) || 0);
    const totalFF = Math.max(0, Number(ff) || 0);
    const totalPins = Math.max(0, Number(pins) || 0);
    return Math.max(24.0, Math.sqrt(totalLE + totalFF) * 4.0 + totalPins * 0.6);
  }

  /**
   * Helper to create standard PBR materials configured with dynamic clipping plane
   */
  function createMaterial(colorHex, metalness = 0.8, roughness = 0.25, emissiveHex = 0x000000) {
    const matConfig = {
      color: colorHex,
      metalness: metalness,
      roughness: roughness,
      emissive: emissiveHex
    };
    if (clipPlane) {
      matConfig.clippingPlanes = [clipPlane];
      matConfig.clipShadows = true;
    }
    return new THREE.MeshStandardMaterial(matConfig);
  }

  /**
   * Creates a billboard 2D Canvas sprite for pin labeling
   */
  function createPinLabelSprite(text, dir) {
    const canvas = document.createElement('canvas');
    canvas.width = 256;
    canvas.height = 64;
    const ctx = canvas.getContext('2d');

    // Rounded pill background
    ctx.fillStyle = 'rgba(11, 15, 25, 0.90)';
    if (typeof ctx.roundRect === 'function') {
      ctx.roundRect(4, 4, 248, 56, 12);
    } else {
      ctx.fillRect(4, 4, 248, 56);
    }
    ctx.fill();

    const isClk = text.toLowerCase().includes('clk') || text.toLowerCase().includes('clock');
    const isRst = text.toLowerCase().includes('rst') || text.toLowerCase().includes('reset');
    const isOut = dir === 'output';

    let strokeCol = '#00e5ff'; // Cyan for inputs
    let badge = '[IN]';
    if (isClk) {
      strokeCol = '#76ff03'; // Neon green for clock
      badge = '[CLK]';
    } else if (isRst) {
      strokeCol = '#ff9100'; // Amber for reset
      badge = '[RST]';
    } else if (isOut) {
      strokeCol = '#f43f5e'; // Magenta/Rose for outputs
      badge = '[OUT]';
    }

    ctx.strokeStyle = strokeCol;
    ctx.lineWidth = 3;
    ctx.stroke();

    ctx.font = 'bold 22px "JetBrains Mono", Consolas, monospace';
    ctx.fillStyle = strokeCol;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(`${badge} ${text}`, 128, 32);

    const texture = new THREE.CanvasTexture(canvas);
    texture.minFilter = THREE.LinearFilter;
    const spriteMat = new THREE.SpriteMaterial({
      map: texture,
      depthTest: false,
      sizeAttenuation: true
    });
    const sprite = new THREE.Sprite(spriteMat);
    sprite.scale.set(2.4, 0.6, 1.0);
    return sprite;
  }

  /**
   * Initializes the Three.js 3D viewport inside the specified container
   */
  function initChip3D(containerId, options = {}) {
    if (!window.THREE) {
      console.error('Three.js library is not loaded. Ensure /assets/three.min.js is included.');
      return null;
    }

    // Resolve container element
    containerEl = typeof containerId === 'string' ? document.getElementById(containerId) : containerId;
    if (!containerEl) {
      // Fallback: check alternate IDs
      containerEl = document.getElementById('chip3d-container') || document.getElementById('chip3d-canvas-container');
    }
    if (!containerEl) {
      console.warn('initChip3D: Target DOM container not found for ID:', containerId);
      return null;
    }

    // Clean any prior children
    containerEl.innerHTML = '';
    const width = containerEl.clientWidth || 800;
    const height = containerEl.clientHeight || 520;

    // 1. Scene setup
    scene = new THREE.Scene();
    scene.background = new THREE.Color(0x0b0f19);

    // 2. Dynamic WebGL Clipping Plane Setup
    clipPlane = new THREE.Plane(new THREE.Vector3(0, -1, 0), 2.5);

    // 3. Camera Setup
    camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000);

    // 4. WebGL Renderer Setup
    try {
      renderer = new THREE.WebGLRenderer({
        antialias: true,
        alpha: true,
        powerPreference: 'high-performance'
      });
    } catch (e) {
      console.error('WebGL Initialization Failed:', e);
      containerEl.innerHTML = '<div style="color:#ef4444;padding:2rem;text-align:center;">WebGL không khả dụng trên trình duyệt của bạn.</div>';
      return null;
    }

    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.localClippingEnabled = true;
    containerEl.appendChild(renderer.domElement);

    // 5. OrbitControls Setup
    if (THREE.OrbitControls) {
      controls = new THREE.OrbitControls(camera, renderer.domElement);
      controls.enableDamping = true;
      controls.dampingFactor = 0.05;
      controls.minDistance = 6.0;
      controls.maxDistance = 300.0;
    }

    // 6. Professional Studio Lighting Rig
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.75);
    scene.add(ambientLight);

    const dirLightKey = new THREE.DirectionalLight(0xffffff, 0.9);
    dirLightKey.position.set(45, 75, 45);
    scene.add(dirLightKey);

    const dirLightFill = new THREE.DirectionalLight(0x00e5ff, 0.35);
    dirLightFill.position.set(-45, 35, -45);
    scene.add(dirLightFill);

    const dirLightRim = new THREE.DirectionalLight(0xffd54f, 0.25);
    dirLightRim.position.set(0, -40, 50);
    scene.add(dirLightRim);

    // 7. Initialize 8 Dedicated Layer Groups
    for (const key of Object.keys(groups)) {
      groups[key] = new THREE.Group();
      scene.add(groups[key]);
    }

    // 8. Initial Geometry Population with Default Canonical Multiplier (8-bit)
    const initialData = options.defaultData || {
      entity: 'nhan_8_bit',
      category: 'MULTIPLIER',
      logic_elements: 17,
      total_registers: 16,
      total_pins: 34,
      ports: [
        { name: 'clk', dir: 'input', width: 1 },
        { name: 'rst', dir: 'input', width: 1 },
        { name: 'a', dir: 'input', width: 8 },
        { name: 'b', dir: 'input', width: 8 },
        { name: 'product', dir: 'output', width: 16 }
      ]
    };
    updateChipGeometry(initialData);

    // 9. Resize Handling
    const handleResize = () => {
      if (!containerEl || !renderer || !camera) return;
      const w = containerEl.clientWidth || 800;
      const h = containerEl.clientHeight || 520;
      if (w === 0 || h === 0) return;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };
    window.addEventListener('resize', handleResize);

    // 10. Animation Render Loop
    const animate = () => {
      animFrameId = requestAnimationFrame(animate);
      if (controls) controls.update();
      if (renderer && scene && camera) {
        renderer.render(scene, camera);
      }
    };
    animate();

    return {
      update: updateChipGeometry,
      updateChipGeometry: updateChipGeometry,
      toggleLayer: toggleLayer,
      setClippingPlane: setClippingPlane,
      resetCamera: resetCamera,
      getDieDimension: () => currentDieDimension,
      dispose: () => {
        if (animFrameId) cancelAnimationFrame(animFrameId);
        window.removeEventListener('resize', handleResize);
        if (renderer && renderer.domElement) {
          renderer.domElement.remove();
        }
      }
    };
  }

  /**
   * Reconstructs procedural 3D chip geometry based on synthesized hardware parameters
   */
  function updateChipGeometry(data = {}) {
    if (!scene) return;

    // Clear previous geometries and meshes across all groups
    for (const key of Object.keys(groups)) {
      const grp = groups[key];
      while (grp.children.length > 0) {
        const obj = grp.children[0];
        if (obj.geometry) obj.geometry.dispose();
        if (obj.material) {
          if (Array.isArray(obj.material)) {
            obj.material.forEach(m => m.dispose());
          } else {
            obj.material.dispose();
          }
        }
        grp.remove(obj);
      }
    }

    const le = Number(data.logic_elements !== undefined ? data.logic_elements : 17);
    const ff = Number(data.total_registers !== undefined ? data.total_registers : 16);
    const pins = Number(data.total_pins !== undefined ? data.total_pins : 34);
    const ports = Array.isArray(data.ports) ? data.ports : [];
    const entity = (data.entity || 'nhan_8_bit').toLowerCase();
    const category = (data.category || (entity.includes('nhan') ? 'MULTIPLIER' : 'GENERAL')).toUpperCase();

    // 1. Calculate Exact Die Dimension
    const D = calcDieDimension(le, ff, pins);
    currentDieDimension = D;
    const halfD = D / 2.0;

    // Update HUD information elements if present in DOM
    const hudNameEl = document.getElementById('hud-chip-name');
    if (hudNameEl) hudNameEl.textContent = `Chip: ${entity.toUpperCase()}`;
    const hudDimEl = document.getElementById('hud-chip-dim');
    if (hudDimEl) hudDimEl.textContent = `Die: ${D.toFixed(1)} × ${D.toFixed(1)} mm² | LEs: ${le} | FFs: ${ff} | Pins: ${pins}`;

    // 2. LAYER 1: SILICON SUBSTRATE DIE & SEAL RING
    // Surface at Y = 0.0, base at Y = -1.6 (Height = 1.6, Center Y = -0.8)
    const subGeo = new THREE.BoxGeometry(D, 1.6, D);
    const subMat = createMaterial(0x0f172a, 0.85, 0.35); // Dark metallic blue-gray
    const subMesh = new THREE.Mesh(subGeo, subMat);
    subMesh.position.set(0, -0.8, 0);
    groups.substrate.add(subMesh);

    // Bevel Guard Scribe Seal Ring around perimeter
    const ringGeo = new THREE.BoxGeometry(D + 0.4, 0.2, D + 0.4);
    const ringMat = createMaterial(0x334155, 0.9, 0.25);
    const ringMesh = new THREE.Mesh(ringGeo, ringMat);
    ringMesh.position.set(0, 0.1, 0);
    groups.substrate.add(ringMesh);

    // Substrate Grid pattern on active surface
    const gridHelper = new THREE.GridHelper(D - 2.0, Math.max(8, Math.floor(D / 2.5)), 0x1e293b, 0x1e293b);
    gridHelper.position.set(0, 0.01, 0);
    groups.substrate.add(gridHelper);

    // 3. LAYER 2: STANDARD CELLS & LOGIC BLOCKS (Y in [0.0, 0.45])
    const coreW = D - 6.0;
    const coreL = D - 6.0;

    // Dedicated Registers (Flip-Flops) in dual columns flanking the central clock spine
    const regCount = Math.max(4, Math.min(64, ff));
    const regGeo = new THREE.BoxGeometry(0.9, 0.45, 0.7);
    const regMat = createMaterial(0xff9100, 0.4, 0.3); // Amber #ff9100
    const cvGeo = new THREE.CylinderGeometry(0.1, 0.1, 0.2, 8);
    const cvMat = createMaterial(0xffc107, 0.95, 0.15); // Tungsten / Brass #ffc107

    for (let i = 0; i < regCount; i++) {
      const zPos = -coreL / 2 + 2.0 + (i / Math.max(1, regCount - 1)) * (coreL - 4.0);
      const side = (i % 2 === 0) ? -1.3 : 1.3;
      const regMesh = new THREE.Mesh(regGeo, regMat);
      regMesh.position.set(side, 0.225, zPos);
      groups.cells.add(regMesh);

      // Contact Via connecting register to M1 (Y in [0.45, 0.65], center Y = 0.55)
      const cvMesh = new THREE.Mesh(cvGeo, cvMat);
      cvMesh.position.set(side, 0.55, zPos);
      groups.vias.add(cvMesh);
    }

    // Combinational Logic Gates distributed in row tracks
    const combCount = Math.max(6, Math.min(80, le - ff > 0 ? le - ff : Math.floor(le * 0.75) + 4));
    const combGeo = new THREE.BoxGeometry(0.8, 0.45, 0.6);
    const combMat = createMaterial(0x00e5ff, 0.45, 0.35); // Cyan #00e5ff
    const numRows = Math.max(3, Math.floor(coreL / 2.0));

    for (let i = 0; i < combCount; i++) {
      const rowIdx = i % numRows;
      const zPos = -coreL / 2 + 1.5 + rowIdx * (coreL / Math.max(1, numRows));
      const colStep = (coreW - 4.0) / Math.max(1, Math.ceil(combCount / numRows));
      const colIdx = Math.floor(i / numRows);
      const xOffset = -coreW / 2 + 2.0 + colIdx * colStep;
      if (Math.abs(xOffset) < 2.0) continue; // Keep central clock corridor unobstructed

      const combMesh = new THREE.Mesh(combGeo, combMat);
      combMesh.position.set(xOffset, 0.225, zPos);
      groups.cells.add(combMesh);

      // Random Contact Vias connecting logic to M1
      if (i % 2 === 0) {
        const combVia = new THREE.Mesh(cvGeo, cvMat);
        combVia.position.set(xOffset, 0.55, zPos);
        groups.vias.add(combVia);
      }
    }

    // Multiplier Systolic Array (Category-specific for Multipliers)
    if (category.includes('MULTIPLIER') || entity.includes('nhan') || entity.includes('mult')) {
      const multGeo = new THREE.BoxGeometry(0.75, 0.45, 0.75);
      const multMat = createMaterial(0x2979ff, 0.6, 0.2); // Deep Blue #2979ff
      const gridSize = 4;
      for (let r = 0; r < gridSize; r++) {
        for (let c = 0; c < gridSize; c++) {
          const mMesh = new THREE.Mesh(multGeo, multMat);
          mMesh.position.set(2.4 + c * 1.3, 0.225, -2.4 + r * 1.3);
          groups.cells.add(mMesh);
        }
      }
    }

    // FSM State Controller Block (Category-specific for FSM / Counters)
    if (category.includes('FSM') || entity.includes('gray') || entity.includes('vending') || entity.includes('elevator') || entity.includes('counter')) {
      const fsmGeo = new THREE.BoxGeometry(3.0, 0.5, 3.0);
      const fsmMat = createMaterial(0xd500f9, 0.55, 0.25); // Royal Purple #d500f9
      const fsmMesh = new THREE.Mesh(fsmGeo, fsmMat);
      fsmMesh.position.set(0, 0.25, 0);
      groups.cells.add(fsmMesh);
    }

    // 4. LAYER 3: METAL 1 (M1 — Horizontal Local Routing, Y = 0.65)
    const m1Mat = createMaterial(0x4fc3f7, 0.8, 0.2); // Sky Blue #4fc3f7
    for (let r = 0; r < numRows; r++) {
      const zPos = -coreL / 2 + 1.5 + r * (coreL / Math.max(1, numRows));
      const m1Geo = new THREE.BoxGeometry(coreW, 0.08, 0.25);
      const m1Mesh = new THREE.Mesh(m1Geo, m1Mat);
      m1Mesh.position.set(0, 0.65, zPos);
      groups.m1.add(m1Mesh);
    }

    // 5. LAYER 4: METAL 2 (M2 — Vertical Orthogonal Cross-Row Routing, Y = 1.20)
    const m2Mat = createMaterial(0xffd54f, 0.85, 0.2); // Gold / Amber #ffd54f
    const numCols = Math.max(4, Math.floor(coreW / 2.5));
    const v12Geo = new THREE.CylinderGeometry(0.12, 0.12, 0.55, 8);
    const v12Mat = createMaterial(0xffc107, 0.95, 0.15); // Tungsten / Brass

    for (let c = 0; c < numCols; c++) {
      const xPos = -coreW / 2 + 1.5 + c * (coreW / Math.max(1, numCols - 1));
      const m2Geo = new THREE.BoxGeometry(0.3, 0.08, coreL);
      const m2Mesh = new THREE.Mesh(m2Geo, m2Mat);
      m2Mesh.position.set(xPos, 1.20, 0);
      groups.m2.add(m2Mesh);

      // Via 12 connecting M1 to M2 at grid intersections (Y in [0.65, 1.20], center Y = 0.925)
      for (let r = 0; r < numRows; r++) {
        if ((r + c) % 2 === 0) {
          const zPos = -coreL / 2 + 1.5 + r * (coreL / Math.max(1, numRows));
          const v12Mesh = new THREE.Mesh(v12Geo, v12Mat);
          v12Mesh.position.set(xPos, 0.925, zPos);
          groups.vias.add(v12Mesh);
        }
      }
    }

    // 6. LAYER 5: METAL 3 (M3 — Global Power Grid & Clock Spine, Y = 1.85)
    const vddMat = createMaterial(0xff1744, 0.9, 0.15, 0x330005); // VDD Ruby Red #ff1744
    const vssMat = createMaterial(0x00b0ff, 0.9, 0.15, 0x001133); // VSS Electric Blue #00b0ff
    const clkMat = createMaterial(0x76ff03, 0.95, 0.1, 0x113300); // Clock Neon Green #76ff03

    // Central High-Speed Clock Distribution Spine along Z-axis (X = 0)
    const clkGeo = new THREE.BoxGeometry(0.5, 0.12, coreL + 2.0);
    const clkMesh = new THREE.Mesh(clkGeo, clkMat);
    clkMesh.position.set(0, 1.85, 0);
    groups.m3.add(clkMesh);

    // Interleaved Power Mesh Rails (VDD and VSS) protecting against IR-drop
    const numRails = Math.max(3, Math.floor(coreW / 3.8));
    const v23Geo = new THREE.CylinderGeometry(0.14, 0.14, 0.65, 8);
    const v23Mat = createMaterial(0xffc107, 0.95, 0.15); // Via 23

    for (let i = 0; i < numRails; i++) {
      const xPos = -coreW / 2 + 2.0 + i * (coreW / Math.max(1, numRails - 1));
      if (Math.abs(xPos) < 1.0) continue; // Keep clock corridor clear
      const isVdd = (i % 2 === 0);
      const railGeo = new THREE.BoxGeometry(0.42, 0.12, coreL);
      const railMesh = new THREE.Mesh(railGeo, isVdd ? vddMat : vssMat);
      railMesh.position.set(xPos, 1.85, 0);
      groups.m3.add(railMesh);

      // Via 23 connecting M2 to M3 (Y in [1.20, 1.85], center Y = 1.525)
      for (let c = 0; c < 3; c++) {
        const zTap = -coreL / 3 + c * (coreL / 3);
        const v23Mesh = new THREE.Mesh(v23Geo, v23Mat);
        v23Mesh.position.set(xPos, 1.525, zTap);
        groups.vias.add(v23Mesh);
      }
    }

    // 7. LAYER 6: PERIPHERAL I/O BONDING PADS, WIRE BONDS & BILLBOARD LABELS
    const padInset = 1.2;
    const padY = 0.06;
    const padGeo = new THREE.BoxGeometry(1.4, 0.12, 1.4);
    const padMat = createMaterial(0xffd700, 0.95, 0.1); // Gold #ffd700

    // Construct flat list of pin terminals
    const pinList = [];
    if (ports.length > 0) {
      ports.forEach(p => {
        const w = Number(p.width) || 1;
        const name = p.name || 'pin';
        const dir = p.dir || 'input';
        if (w > 1 && name !== 'clk' && name !== 'rst') {
          for (let b = 0; b < w; b++) {
            pinList.push({ name: `${name}[${b}]`, dir: dir, isBus: true });
          }
        } else {
          pinList.push({ name: name, dir: dir, isBus: false });
        }
      });
    } else {
      // Default fallback pins
      for (let i = 0; i < pins; i++) {
        pinList.push({
          name: i < pins / 2 ? `in_${i}` : `out_${i - Math.floor(pins / 2)}`,
          dir: i < pins / 2 ? 'input' : 'output'
        });
      }
    }

    const totalPins = pinList.length;
    const pinsPerSide = Math.ceil(totalPins / 4.0);

    pinList.forEach((pin, idx) => {
      const side = Math.floor(idx / pinsPerSide); // 0: West, 1: South, 2: East, 3: North
      const posInSide = idx % pinsPerSide;
      const step = (D - 2 * padInset - 2.0) / Math.max(1, pinsPerSide - 1);
      const offset = -(halfD - padInset - 1.0) + posInSide * step;

      let px = 0, pz = 0;
      if (side === 0) {
        px = -halfD + padInset;
        pz = offset;
      } else if (side === 1) {
        px = offset;
        pz = halfD - padInset;
      } else if (side === 2) {
        px = halfD - padInset;
        pz = -offset;
      } else {
        px = -offset;
        pz = -halfD + padInset;
      }

      // Bonding Pad Mesh
      const padMesh = new THREE.Mesh(padGeo, padMat);
      padMesh.position.set(px, padY, pz);
      groups.pads.add(padMesh);

      // Realistic 3D Arched Wire Bond to package leadframe
      const pStart = new THREE.Vector3(px, padY, pz);
      const pMid = new THREE.Vector3(px * 1.25, 2.2, pz * 1.25);
      const pEnd = new THREE.Vector3(px * 1.45, -0.6, pz * 1.45);
      const curve = new THREE.QuadraticBezierCurve3(pStart, pMid, pEnd);
      const tubeGeo = new THREE.TubeGeometry(curve, 16, 0.045, 8, false);
      const tubeMat = createMaterial(0xffd700, 0.95, 0.1);
      const tubeMesh = new THREE.Mesh(tubeGeo, tubeMat);
      groups.pads.add(tubeMesh);

      // 3D Billboard Sprite Label
      const sprite = createPinLabelSprite(pin.name, pin.dir);
      sprite.position.set(px, 1.8, pz);
      groups.labels.add(sprite);
    });

    // Reset Camera view to optimal isometric distance
    resetCamera(D);
  }

  /**
   * Toggles visibility for any of the 8 dedicated layer groups
   */
  function toggleLayer(layerName, isVisible) {
    if (groups[layerName]) {
      groups[layerName].visible = Boolean(isVisible);
    }
  }

  /**
   * Sets dynamic cross-section clipping plane height
   * Accepts either normalized percentage (0.0 .. 1.0) or exact Y elevation (-1.6 .. +2.5)
   */
  function setClippingPlane(value) {
    if (!clipPlane) return;
    const num = Number(value);
    let yVal = 2.5;

    if (num >= -1.6 && num <= 2.5) {
      yVal = num;
    } else {
      // Treat as percentage 0..1
      const p = Math.max(0.0, Math.min(1.0, num));
      yVal = -1.6 + p * 4.1;
    }

    clipPlane.constant = yVal;

    // Update clipping readout label if present in DOM
    const labelEl = document.getElementById('clipping-val-label') || document.getElementById('label-clipping-value');
    if (labelEl) {
      labelEl.textContent = `Cao độ Y: ${yVal >= 0 ? '+' : ''}${yVal.toFixed(2)}`;
    }
  }

  /**
   * Resets camera to standard isometric CAD view
   */
  function resetCamera(customD) {
    if (!camera || !controls) return;
    const D = customD || currentDieDimension || 43.38;
    camera.position.set(D * 0.85, D * 0.75, D * 1.05);
    camera.lookAt(0, 0, 0);
    controls.target.set(0, 0, 0);
    controls.update();
  }

  // Export Unified Global Interface
  window.Chip3D = {
    init: initChip3D,
    update: updateChipGeometry,
    updateChipGeometry: updateChipGeometry,
    toggleLayer: toggleLayer,
    setClippingPlane: setClippingPlane,
    resetCamera: resetCamera,
    calcDieDimension: calcDieDimension
  };

  // Backward Compatibility Globals
  window.initChip3D = initChip3D;
  window.updateChipGeometry = updateChipGeometry;

})(window);
