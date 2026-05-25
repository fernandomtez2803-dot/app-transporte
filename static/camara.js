/* ══════════════════════════════════════════════
   Cámara + YOLO + Cubicaje — Lógica principal
   ══════════════════════════════════════════════ */

// ── Estado global ──
const CAM = {
  stream: null,
  video: null,
  canvas: null,
  ctx: null,
  capturedImage: null,       // ImageData del frame capturado
  detections: [],            // Resultados YOLO
  calibration: {
    active: false,           // Modo calibración activo
    points: [],              // [{x, y}, {x, y}]
    refDistanceCm: 120,      // Distancia de referencia en cm (euro pallet largo)
    pxPerCm: null            // Ratio calculado
  },
  measuring: {
    active: false,           // Modo medición activo
    points: [],              // [{x, y}, {x, y}]
    target: null             // 'largo', 'ancho', 'alto'
  },
  dimensions: {
    largo: 0,
    ancho: 0,
    alto: 0
  }
};

// ── Inicialización ──
document.addEventListener('DOMContentLoaded', () => {
  CAM.video = document.getElementById('webcam');
  CAM.canvas = document.getElementById('detection-canvas');
  CAM.ctx = CAM.canvas.getContext('2d');

  // Enumerar cámaras disponibles
  enumerarCamaras();

  // Eventos de canvas para calibración/medición
  CAM.canvas.addEventListener('click', handleCanvasClick);

  // Eventos de inputs de dimensiones
  ['dim-largo', 'dim-ancho', 'dim-alto'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.addEventListener('input', calcularVolumen);
  });
});


// ════════════════════════════════════════
// TABS
// ════════════════════════════════════════
function switchTab(tabName) {
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

  document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');
  document.getElementById(`tab-${tabName}`).classList.add('active');
}


// ════════════════════════════════════════
// CÁMARA
// ════════════════════════════════════════
async function enumerarCamaras() {
  try {
    // Necesitamos pedir permiso primero para ver las cámaras
    await navigator.mediaDevices.getUserMedia({ video: true }).then(s => s.getTracks().forEach(t => t.stop()));

    const devices = await navigator.mediaDevices.enumerateDevices();
    const videoDevices = devices.filter(d => d.kind === 'videoinput');
    const select = document.getElementById('camera-select');

    select.innerHTML = '';

    // Palabras clave para identificar cámaras externas (prioridad)
    const externalKeywords = ['imou', 'ranger', 'usb', 'external', 'ip cam', 'hikvision', 'dahua', 'reolink'];
    // Palabras clave para identificar la webcam integrada (evitar)
    const builtinKeywords = ['integrated', 'built-in', 'front', 'facetime', 'ir camera', 'laptop'];

    let bestIndex = -1;

    videoDevices.forEach((dev, i) => {
      const opt = document.createElement('option');
      opt.value = dev.deviceId;
      const label = dev.label || `Cámara ${i + 1}`;
      opt.textContent = label;
      select.appendChild(opt);

      const labelLower = label.toLowerCase();

      // Buscar cámara externa por nombre
      if (bestIndex === -1) {
        const isExternal = externalKeywords.some(kw => labelLower.includes(kw));
        const isBuiltin = builtinKeywords.some(kw => labelLower.includes(kw));

        if (isExternal) {
          bestIndex = i; // Prioridad máxima: cámara externa detectada por nombre
        } else if (!isBuiltin && videoDevices.length > 1 && i > 0) {
          bestIndex = i; // Prioridad media: no es integrada y no es la primera (la primera suele ser la integrada)
        }
      }
    });

    // Si encontramos una cámara externa, seleccionarla
    if (bestIndex >= 0) {
      select.selectedIndex = bestIndex;
      console.log(`Auto-seleccionada cámara externa: ${videoDevices[bestIndex].label}`);
    } else if (videoDevices.length > 1) {
      // Si hay varias y no detectamos externa, elegir la última (suele ser la USB)
      select.selectedIndex = videoDevices.length - 1;
    }

    // Mostrar cuántas cámaras hay
    if (videoDevices.length > 1) {
      setStatus('info', `📹 ${videoDevices.length} cámaras detectadas — seleccionada: ${select.options[select.selectedIndex]?.text}`);
    }

  } catch (e) {
    console.warn('No se pudieron enumerar cámaras:', e);
  }
}

async function iniciarCamara() {
  const select = document.getElementById('camera-select');
  const deviceId = select.value;

  try {
    const constraints = {
      video: {
        deviceId: deviceId ? { exact: deviceId } : undefined,
        width: { ideal: 1280 },
        height: { ideal: 960 }
      }
    };

    CAM.stream = await navigator.mediaDevices.getUserMedia(constraints);
    CAM.video.srcObject = CAM.stream;
    await CAM.video.play();

    // Ajustar canvas al tamaño del vídeo
    CAM.video.addEventListener('loadedmetadata', () => {
      CAM.canvas.width = CAM.video.videoWidth;
      CAM.canvas.height = CAM.video.videoHeight;
    });

    // UI
    document.getElementById('camera-placeholder').classList.add('hidden');
    document.getElementById('btn-start-cam').style.display = 'none';
    document.getElementById('btn-stop-cam').style.display = 'flex';
    document.getElementById('btn-capture').disabled = false;

    setStatus('success', '✅ Cámara conectada');
  } catch (e) {
    setStatus('error', '❌ Error al acceder a la cámara: ' + e.message);
  }
}

function detenerCamara() {
  if (CAM.stream) {
    CAM.stream.getTracks().forEach(t => t.stop());
    CAM.stream = null;
  }
  CAM.video.srcObject = null;

  document.getElementById('camera-placeholder').classList.remove('hidden');
  document.getElementById('btn-start-cam').style.display = 'flex';
  document.getElementById('btn-stop-cam').style.display = 'none';
  document.getElementById('btn-capture').disabled = true;

  limpiarCanvas();
  setStatus('info', 'Cámara detenida');
}

function capturarFrame() {
  if (!CAM.stream) return;

  // Dibujar frame actual en el canvas
  CAM.canvas.width = CAM.video.videoWidth;
  CAM.canvas.height = CAM.video.videoHeight;
  CAM.ctx.drawImage(CAM.video, 0, 0);

  // Guardar imagen capturada
  CAM.capturedImage = CAM.ctx.getImageData(0, 0, CAM.canvas.width, CAM.canvas.height);

  // Pausar vídeo para mostrar la captura
  CAM.video.pause();

  // Habilitar detección
  document.getElementById('btn-detect').disabled = false;
  document.getElementById('btn-calibrate').disabled = false;

  setStatus('success', '📸 Frame capturado. Pulsa "Detectar" para analizar con YOLO.');
}

function volverALive() {
  if (CAM.stream) {
    CAM.video.play();
    limpiarCanvas();
    CAM.detections = [];
    CAM.capturedImage = null;
    document.getElementById('btn-detect').disabled = true;
    actualizarListaDetecciones();
    setStatus('info', 'Modo en vivo');
  }
}


// ════════════════════════════════════════
// DETECCIÓN YOLO
// ════════════════════════════════════════
async function detectarYOLO() {
  if (!CAM.capturedImage) {
    setStatus('error', 'Primero captura un frame');
    return;
  }

  setStatus('loading', '🔍 Analizando imagen con YOLO...');
  document.getElementById('btn-detect').disabled = true;

  try {
    // Convertir canvas a base64
    const tempCanvas = document.createElement('canvas');
    tempCanvas.width = CAM.canvas.width;
    tempCanvas.height = CAM.canvas.height;
    const tempCtx = tempCanvas.getContext('2d');
    tempCtx.putImageData(CAM.capturedImage, 0, 0);
    const imageData = tempCanvas.toDataURL('image/jpeg', 0.85);

    // Enviar al backend
    const resp = await fetch('/api/detectar', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ image: imageData })
    });

    const data = await resp.json();
    if (!resp.ok) throw new Error(data.error || 'Error desconocido');

    CAM.detections = data.detections || [];

    // Dibujar detecciones
    dibujarDetecciones();
    actualizarListaDetecciones();

    setStatus('success', `✅ ${CAM.detections.length} objeto(s) detectado(s)`);
  } catch (e) {
    setStatus('error', '❌ Error en detección: ' + e.message);
  }

  document.getElementById('btn-detect').disabled = false;
}

function dibujarDetecciones() {
  if (!CAM.capturedImage) return;

  // Redibujar la imagen capturada
  CAM.ctx.putImageData(CAM.capturedImage, 0, 0);

  const scaleX = CAM.canvas.width / CAM.canvas.width; // 1:1 ya que usamos dimensiones reales
  const scaleY = CAM.canvas.height / CAM.canvas.height;

  const colors = {
    'person': '#e74c3c',
    'car': '#3498db',
    'truck': '#2ecc71',
    'box': '#f39c12',
    'suitcase': '#9b59b6',
    'default': '#2e86c1'
  };

  CAM.detections.forEach(det => {
    const color = colors[det.class] || colors.default;
    const x = det.x1;
    const y = det.y1;
    const w = det.width;
    const h = det.height;

    // Bounding box
    CAM.ctx.strokeStyle = color;
    CAM.ctx.lineWidth = 3;
    CAM.ctx.strokeRect(x, y, w, h);

    // Fondo del label
    const label = `${det.class} ${(det.confidence * 100).toFixed(0)}%`;
    CAM.ctx.font = 'bold 14px Segoe UI';
    const textWidth = CAM.ctx.measureText(label).width;

    CAM.ctx.fillStyle = color;
    CAM.ctx.fillRect(x, y - 22, textWidth + 10, 22);

    CAM.ctx.fillStyle = 'white';
    CAM.ctx.fillText(label, x + 5, y - 6);
  });

  // Dibujar puntos de calibración si existen
  dibujarPuntosCalibración();
  dibujarPuntosMedición();
}

function actualizarListaDetecciones() {
  const lista = document.getElementById('detection-list');
  if (CAM.detections.length === 0) {
    lista.innerHTML = '<p class="detection-empty">Sin detecciones</p>';
    return;
  }

  lista.innerHTML = CAM.detections.map(det => `
    <div class="detection-item">
      <span class="detection-class">${esc(det.class)}</span>
      <span class="detection-conf">${(det.confidence * 100).toFixed(0)}%</span>
    </div>
  `).join('');
}


// ════════════════════════════════════════
// CALIBRACIÓN (referencia pallet)
// ════════════════════════════════════════
function toggleCalibrar() {
  const btn = document.getElementById('btn-calibrate');

  if (CAM.calibration.active) {
    // Cancelar
    CAM.calibration.active = false;
    CAM.calibration.points = [];
    btn.classList.remove('active');
    btn.textContent = '📏 Calibrar referencia';
    CAM.canvas.classList.remove('crosshair-cursor');
    dibujarDetecciones();
    return;
  }

  // Activar modo calibración
  CAM.calibration.active = true;
  CAM.calibration.points = [];
  CAM.measuring.active = false;
  btn.classList.add('active');
  btn.textContent = '❌ Cancelar calibración';
  CAM.canvas.classList.add('crosshair-cursor');

  setStatus('info', '📏 Haz clic en 2 puntos del pallet cuya distancia conozcas (ej: el lado largo = 120cm)');
}

function toggleMedirAltura() {
  const btn = document.getElementById('btn-measure-h');

  if (CAM.measuring.active) {
    CAM.measuring.active = false;
    CAM.measuring.points = [];
    btn.classList.remove('active');
    btn.textContent = '📐 Medir en imagen';
    CAM.canvas.classList.remove('crosshair-cursor');
    dibujarDetecciones();
    return;
  }

  if (!CAM.calibration.pxPerCm) {
    setStatus('error', '⚠ Primero calibra la referencia');
    return;
  }

  CAM.measuring.active = true;
  CAM.measuring.points = [];
  CAM.calibration.active = false;
  btn.classList.add('active');
  btn.textContent = '❌ Cancelar medición';
  CAM.canvas.classList.add('crosshair-cursor');

  // Seleccionar qué dimensión medir
  const target = document.getElementById('measure-target').value;
  CAM.measuring.target = target;

  setStatus('info', `📐 Haz clic en 2 puntos para medir el ${target}`);
}


// ── Manejo de clics en canvas ──
function handleCanvasClick(e) {
  if (!CAM.calibration.active && !CAM.measuring.active) return;

  const rect = CAM.canvas.getBoundingClientRect();
  const scaleX = CAM.canvas.width / rect.width;
  const scaleY = CAM.canvas.height / rect.height;
  const x = (e.clientX - rect.left) * scaleX;
  const y = (e.clientY - rect.top) * scaleY;

  if (CAM.calibration.active) {
    CAM.calibration.points.push({ x, y });
    dibujarDetecciones();

    if (CAM.calibration.points.length === 2) {
      completarCalibración();
    }
  } else if (CAM.measuring.active) {
    CAM.measuring.points.push({ x, y });
    dibujarDetecciones();

    if (CAM.measuring.points.length === 2) {
      completarMedición();
    }
  }
}

function completarCalibración() {
  const p1 = CAM.calibration.points[0];
  const p2 = CAM.calibration.points[1];
  const distPx = Math.sqrt(Math.pow(p2.x - p1.x, 2) + Math.pow(p2.y - p1.y, 2));

  const refCm = parseFloat(document.getElementById('ref-distance').value) || 120;
  CAM.calibration.refDistanceCm = refCm;
  CAM.calibration.pxPerCm = distPx / refCm;

  // Actualizar UI
  CAM.calibration.active = false;
  const btn = document.getElementById('btn-calibrate');
  btn.classList.remove('active');
  btn.textContent = '✅ Recalibrar referencia';
  CAM.canvas.classList.remove('crosshair-cursor');

  document.getElementById('calibration-status').className = 'calibration-status done';
  document.getElementById('calibration-status').textContent =
    `✅ Calibrado: ${CAM.calibration.pxPerCm.toFixed(2)} px/cm (${refCm} cm = ${distPx.toFixed(0)} px)`;

  // Habilitar medición
  document.getElementById('btn-measure-h').disabled = false;

  dibujarDetecciones();
  setStatus('success', `✅ Calibración completada: ${CAM.calibration.pxPerCm.toFixed(2)} px/cm`);
}

function completarMedición() {
  const p1 = CAM.measuring.points[0];
  const p2 = CAM.measuring.points[1];
  const distPx = Math.sqrt(Math.pow(p2.x - p1.x, 2) + Math.pow(p2.y - p1.y, 2));
  const distCm = distPx / CAM.calibration.pxPerCm;

  const target = CAM.measuring.target;
  const inputId = `dim-${target}`;
  document.getElementById(inputId).value = Math.round(distCm);
  CAM.dimensions[target] = Math.round(distCm);

  // Reset medición
  CAM.measuring.active = false;
  const btn = document.getElementById('btn-measure-h');
  btn.classList.remove('active');
  btn.textContent = '📐 Medir en imagen';
  CAM.canvas.classList.remove('crosshair-cursor');

  dibujarDetecciones();
  calcularVolumen();

  setStatus('success', `📐 ${target}: ${Math.round(distCm)} cm (${distPx.toFixed(0)} px)`);
}


// ── Dibujar puntos y líneas ──
function dibujarPuntosCalibración() {
  const pts = CAM.calibration.points;
  if (pts.length === 0) return;

  CAM.ctx.fillStyle = '#f39c12';
  pts.forEach(p => {
    CAM.ctx.beginPath();
    CAM.ctx.arc(p.x, p.y, 6, 0, Math.PI * 2);
    CAM.ctx.fill();
  });

  if (pts.length === 2) {
    CAM.ctx.strokeStyle = '#f39c12';
    CAM.ctx.lineWidth = 2;
    CAM.ctx.setLineDash([6, 4]);
    CAM.ctx.beginPath();
    CAM.ctx.moveTo(pts[0].x, pts[0].y);
    CAM.ctx.lineTo(pts[1].x, pts[1].y);
    CAM.ctx.stroke();
    CAM.ctx.setLineDash([]);

    // Mostrar distancia
    const midX = (pts[0].x + pts[1].x) / 2;
    const midY = (pts[0].y + pts[1].y) / 2;
    const refCm = CAM.calibration.refDistanceCm;
    CAM.ctx.font = 'bold 16px Segoe UI';
    CAM.ctx.fillStyle = '#f39c12';
    CAM.ctx.fillText(`${refCm} cm (ref)`, midX + 10, midY - 10);
  }
}

function dibujarPuntosMedición() {
  const pts = CAM.measuring.points;
  if (pts.length === 0) return;

  CAM.ctx.fillStyle = '#3498db';
  pts.forEach(p => {
    CAM.ctx.beginPath();
    CAM.ctx.arc(p.x, p.y, 6, 0, Math.PI * 2);
    CAM.ctx.fill();
  });

  if (pts.length === 2 && CAM.calibration.pxPerCm) {
    CAM.ctx.strokeStyle = '#3498db';
    CAM.ctx.lineWidth = 2;
    CAM.ctx.setLineDash([6, 4]);
    CAM.ctx.beginPath();
    CAM.ctx.moveTo(pts[0].x, pts[0].y);
    CAM.ctx.lineTo(pts[1].x, pts[1].y);
    CAM.ctx.stroke();
    CAM.ctx.setLineDash([]);

    // Mostrar distancia real
    const distPx = Math.sqrt(Math.pow(pts[1].x - pts[0].x, 2) + Math.pow(pts[1].y - pts[0].y, 2));
    const distCm = distPx / CAM.calibration.pxPerCm;
    const midX = (pts[0].x + pts[1].x) / 2;
    const midY = (pts[0].y + pts[1].y) / 2;
    CAM.ctx.font = 'bold 16px Segoe UI';
    CAM.ctx.fillStyle = '#3498db';
    CAM.ctx.fillText(`${Math.round(distCm)} cm`, midX + 10, midY - 10);
  }
}


// ════════════════════════════════════════
// CUBICAJE
// ════════════════════════════════════════
function calcularVolumen() {
  const largo = parseFloat(document.getElementById('dim-largo').value) || 0;
  const ancho = parseFloat(document.getElementById('dim-ancho').value) || 0;
  const alto = parseFloat(document.getElementById('dim-alto').value) || 0;

  CAM.dimensions = { largo, ancho, alto };

  const volM3 = (largo * ancho * alto) / 1000000; // cm³ → m³

  document.getElementById('volume-value').textContent = volM3.toFixed(3);
  document.getElementById('volume-detail').textContent =
    `${largo} × ${ancho} × ${alto} cm`;

  document.getElementById('btn-use-volume').disabled = volM3 <= 0;
}

function usarEnComparador() {
  const volM3 = parseFloat(document.getElementById('volume-value').textContent) || 0;
  if (volM3 <= 0) return;

  // Cambiar a pestaña comparador
  switchTab('comparador');

  // Rellenar campo de volumen
  const volInput = document.getElementById('volumen_m3');
  if (volInput) {
    volInput.value = volM3.toFixed(3);
    volInput.style.borderColor = '#27ae60';
    volInput.style.background = '#eafaf1';
    setTimeout(() => {
      volInput.style.borderColor = '';
      volInput.style.background = '';
    }, 2000);
  }
}


// ════════════════════════════════════════
// UTILIDADES
// ════════════════════════════════════════
function limpiarCanvas() {
  CAM.ctx.clearRect(0, 0, CAM.canvas.width, CAM.canvas.height);
  CAM.detections = [];
  CAM.capturedImage = null;
  actualizarListaDetecciones();
}

function setStatus(type, msg) {
  const el = document.getElementById('cam-status');
  el.className = `status-msg ${type}`;
  el.textContent = msg;
}

function esc(str) {
  return String(str || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}
