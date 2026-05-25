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
    document.getElementById('btn-detect').disabled = false;

    setStatus('success', '✅ Cámara conectada — pulsa Detectar o activa Tiempo Real');
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
let realtimeActive = false;
let realtimeTimer = null;

async function detectarYOLO() {
  // Si no hay captura pero la cámara está activa → capturar automáticamente
  if (!CAM.capturedImage && CAM.stream) {
    capturarFrame();
  }

  if (!CAM.capturedImage) {
    setStatus('error', '❌ Inicia la cámara primero');
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

    if (!realtimeActive) {
      setStatus('success', `✅ ${CAM.detections.length} objeto(s) detectado(s)`);
    }
  } catch (e) {
    if (!realtimeActive) {
      setStatus('error', '❌ Error en detección: ' + e.message);
    }
  }

  document.getElementById('btn-detect').disabled = false;
}

// ── Detección en tiempo real ──
function toggleRealtime() {
  const btn = document.getElementById('btn-realtime');

  if (realtimeActive) {
    // Desactivar
    realtimeActive = false;
    if (realtimeTimer) clearTimeout(realtimeTimer);
    realtimeTimer = null;
    btn.classList.remove('active');
    btn.textContent = '🔴 Tiempo real';
    document.getElementById('btn-detect').disabled = false;
    document.getElementById('btn-capture').disabled = false;
    setStatus('info', 'Detección en tiempo real desactivada');
    return;
  }

  if (!CAM.stream) {
    setStatus('error', '❌ Inicia la cámara primero');
    return;
  }

  // Activar modo tiempo real
  realtimeActive = true;
  btn.classList.add('active');
  btn.textContent = '⏹ Parar tiempo real';
  document.getElementById('btn-detect').disabled = true;
  document.getElementById('btn-capture').disabled = true;
  setStatus('loading', '🔴 Detección en tiempo real activa...');

  loopRealtime();
}

async function loopRealtime() {
  if (!realtimeActive || !CAM.stream) {
    realtimeActive = false;
    return;
  }

  // Capturar frame actual del vídeo directamente
  CAM.canvas.width = CAM.video.videoWidth;
  CAM.canvas.height = CAM.video.videoHeight;
  CAM.ctx.drawImage(CAM.video, 0, 0);
  CAM.capturedImage = CAM.ctx.getImageData(0, 0, CAM.canvas.width, CAM.canvas.height);

  try {
    const tempCanvas = document.createElement('canvas');
    tempCanvas.width = CAM.canvas.width;
    tempCanvas.height = CAM.canvas.height;
    const tempCtx = tempCanvas.getContext('2d');
    tempCtx.putImageData(CAM.capturedImage, 0, 0);
    const imageData = tempCanvas.toDataURL('image/jpeg', 0.7);

    const resp = await fetch('/api/detectar', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ image: imageData })
    });

    const data = await resp.json();
    if (resp.ok) {
      CAM.detections = data.detections || [];

      // Redibujar: frame actual + bounding boxes
      CAM.ctx.drawImage(CAM.video, 0, 0);
      dibujarBoundingBoxes();
      actualizarListaDetecciones();

      const objCount = CAM.detections.length;
      setStatus('loading', `🔴 Tiempo real — ${objCount} objeto(s) detectado(s)`);
    }
  } catch (e) {
    // Silenciar errores en modo real-time para no spammear
  }

  // Siguiente frame (~1 FPS para no saturar el servidor)
  if (realtimeActive) {
    realtimeTimer = setTimeout(loopRealtime, 800);
  }
}

// Dibujar solo los bounding boxes sin tocar la imagen de fondo (para modo realtime)
function dibujarBoundingBoxes() {
  const colors = {
    'person': '#e74c3c',
    'car': '#3498db',
    'truck': '#2ecc71',
    'box': '#f39c12',
    'suitcase': '#9b59b6',
    'bottle': '#1abc9c',
    'cup': '#e67e22',
    'chair': '#95a5a6',
    'default': '#2e86c1'
  };

  CAM.detections.forEach(det => {
    const color = colors[det.class] || colors.default;
    const x = det.x1;
    const y = det.y1;
    const w = det.width;
    const h = det.height;

    // Bounding box con fondo semi-transparente
    CAM.ctx.strokeStyle = color;
    CAM.ctx.lineWidth = 3;
    CAM.ctx.strokeRect(x, y, w, h);

    // Fondo del label
    const label = `${det.class} ${(det.confidence * 100).toFixed(0)}%`;
    CAM.ctx.font = 'bold 14px Segoe UI';
    const textWidth = CAM.ctx.measureText(label).width;

    CAM.ctx.fillStyle = color;
    CAM.ctx.fillRect(x, y - 24, textWidth + 12, 24);

    CAM.ctx.fillStyle = 'white';
    CAM.ctx.fillText(label, x + 6, y - 7);
  });
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

  CAM.detections.forEach((det, i) => {
    const color = colors[det.class] || colors.default;
    const x = det.x1;
    const y = det.y1;
    const w = det.width;
    const h = det.height;

    // Bounding box
    CAM.ctx.strokeStyle = color;
    CAM.ctx.lineWidth = 3;
    CAM.ctx.strokeRect(x, y, w, h);

    // Label con índice
    const label = `#${i+1} ${det.class} ${(det.confidence * 100).toFixed(0)}%`;
    CAM.ctx.font = 'bold 14px Segoe UI';
    const textWidth = CAM.ctx.measureText(label).width;

    CAM.ctx.fillStyle = color;
    CAM.ctx.fillRect(x, y - 22, textWidth + 10, 22);

    CAM.ctx.fillStyle = 'white';
    CAM.ctx.fillText(label, x + 5, y - 6);

    // Si hay estimación, mostrar dimensiones en cm sobre la caja
    if (det._estimatedW && det._estimatedH) {
      const dimLabel = `≈ ${det._estimatedW}×${det._estimatedH} cm`;
      CAM.ctx.font = 'bold 13px Segoe UI';
      const dimWidth = CAM.ctx.measureText(dimLabel).width;
      CAM.ctx.fillStyle = 'rgba(0,0,0,0.7)';
      CAM.ctx.fillRect(x, y + h + 2, dimWidth + 10, 20);
      CAM.ctx.fillStyle = '#2ecc71';
      CAM.ctx.fillText(dimLabel, x + 5, y + h + 16);
    }
  });
}

function actualizarListaDetecciones() {
  const lista = document.getElementById('detection-list');
  const refSelect = document.getElementById('ref-object');

  if (CAM.detections.length === 0) {
    lista.innerHTML = '<p class="detection-empty">Sin detecciones</p>';
    refSelect.innerHTML = '<option value="">— Detecta objetos primero —</option>';
    return;
  }

  // Lista visual
  lista.innerHTML = CAM.detections.map((det, i) => `
    <div class="detection-item">
      <span class="detection-class">#${i+1} ${esc(det.class)}</span>
      <span class="detection-conf">${(det.confidence * 100).toFixed(0)}%</span>
    </div>
  `).join('');

  // Dropdown de referencia
  const prevVal = refSelect.value;
  refSelect.innerHTML = CAM.detections.map((det, i) =>
    `<option value="${i}">#${i+1} ${esc(det.class)} (${Math.round(det.width)}×${Math.round(det.height)} px)</option>`
  ).join('');

  // Seleccionar el más grande por defecto (probablemente el pallet/objeto principal)
  let biggestIdx = 0;
  let biggestArea = 0;
  CAM.detections.forEach((det, i) => {
    const area = det.width * det.height;
    if (area > biggestArea) { biggestArea = area; biggestIdx = i; }
  });
  refSelect.value = prevVal || biggestIdx;
}


// ════════════════════════════════════════
// ESTIMACIÓN AUTOMÁTICA
// ════════════════════════════════════════
function autoEstimar() {
  if (CAM.detections.length === 0) {
    setStatus('error', '❌ Primero detecta objetos con YOLO');
    return;
  }

  const refIdx = parseInt(document.getElementById('ref-object').value);
  const refWidthCm = parseFloat(document.getElementById('ref-width-cm').value) || 120;
  const refHeightCm = parseFloat(document.getElementById('ref-height-cm').value) || 80;

  if (isNaN(refIdx) || !CAM.detections[refIdx]) {
    setStatus('error', '❌ Selecciona un objeto de referencia');
    return;
  }

  const refDet = CAM.detections[refIdx];
  const pxPerCmW = refDet.width / refWidthCm;
  const pxPerCmH = refDet.height / refHeightCm;

  // Anotar dimensiones estimadas en cada detección
  CAM.detections.forEach((det, i) => {
    det._estimatedW = Math.round(det.width / pxPerCmW);
    det._estimatedH = Math.round(det.height / pxPerCmH);
  });

  // Encontrar el objeto más grande que NO sea la referencia (probablemente la carga)
  let targetIdx = -1;
  let targetArea = 0;
  CAM.detections.forEach((det, i) => {
    if (i === refIdx) return;
    const area = det.width * det.height;
    if (area > targetArea) { targetArea = area; targetIdx = i; }
  });

  // Si solo hay un objeto (la referencia), usar ese mismo
  if (targetIdx === -1) targetIdx = refIdx;

  const target = CAM.detections[targetIdx];
  const estLargo = Math.round(target.width / pxPerCmW);
  const estAncho = Math.round(target.width / pxPerCmW); // Asumimos cuadrado en planta si solo vemos un ángulo
  const estAlto = Math.round(target.height / pxPerCmH);

  // Si el target es la referencia, usar las medidas reales proporcionadas
  if (targetIdx === refIdx) {
    document.getElementById('dim-largo').value = refWidthCm;
    document.getElementById('dim-ancho').value = refHeightCm;
    document.getElementById('dim-alto').value = Math.round(refHeightCm * 0.75); // Estimación razonable
  } else {
    document.getElementById('dim-largo').value = estLargo;
    document.getElementById('dim-ancho').value = estLargo; // Mejor aproximación sin vista superior
    document.getElementById('dim-alto').value = estAlto;
  }

  calcularVolumen();

  // Redibujar con dimensiones estimadas
  if (CAM.capturedImage) {
    CAM.ctx.putImageData(CAM.capturedImage, 0, 0);
  }
  dibujarDeteccionesConEstimaciones();

  // Mostrar estado
  const status = document.getElementById('calibration-status');
  status.style.display = 'block';
  status.className = 'calibration-status done';
  status.textContent = `✅ Ratio: ${pxPerCmW.toFixed(2)} px/cm — Ref: ${refDet.class} #${refIdx+1}`;

  setStatus('success', `✅ Dimensiones estimadas automáticamente (puedes ajustar manualmente)`);
}

function dibujarDeteccionesConEstimaciones() {
  const colors = {
    'person': '#e74c3c', 'car': '#3498db', 'truck': '#2ecc71',
    'box': '#f39c12', 'suitcase': '#9b59b6', 'bottle': '#1abc9c',
    'cup': '#e67e22', 'chair': '#95a5a6', 'default': '#2e86c1'
  };

  CAM.detections.forEach((det, i) => {
    const color = colors[det.class] || colors.default;
    const x = det.x1, y = det.y1, w = det.width, h = det.height;

    // Bounding box
    CAM.ctx.strokeStyle = color;
    CAM.ctx.lineWidth = 3;
    CAM.ctx.strokeRect(x, y, w, h);

    // Label
    const label = `#${i+1} ${det.class} ${(det.confidence * 100).toFixed(0)}%`;
    CAM.ctx.font = 'bold 14px Segoe UI';
    const tw = CAM.ctx.measureText(label).width;
    CAM.ctx.fillStyle = color;
    CAM.ctx.fillRect(x, y - 24, tw + 12, 24);
    CAM.ctx.fillStyle = 'white';
    CAM.ctx.fillText(label, x + 6, y - 7);

    // Dimensiones estimadas
    if (det._estimatedW && det._estimatedH) {
      // Ancho (línea horizontal abajo)
      const wLabel = `${det._estimatedW} cm`;
      CAM.ctx.font = 'bold 13px Segoe UI';
      CAM.ctx.fillStyle = '#2ecc71';
      CAM.ctx.fillText(`↔ ${wLabel}`, x + 4, y + h + 16);

      // Alto (línea vertical derecha)
      const hLabel = `${det._estimatedH} cm`;
      CAM.ctx.save();
      CAM.ctx.translate(x + w + 16, y + h / 2);
      CAM.ctx.rotate(-Math.PI / 2);
      CAM.ctx.fillText(`↕ ${hLabel}`, 0, 0);
      CAM.ctx.restore();
    }
  });
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
