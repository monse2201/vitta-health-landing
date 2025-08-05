{% extends "base.html" %}
{% block content %}

<link rel="stylesheet" href="{{ url_for('static', filename='css/grabar_cita.css') }}">

<div class="pagina-scribe">
  <div class="header-form">
    <h1>Escribir</h1>
    <p>Vitta Health escucha tu consulta y genera automáticamente una transcripción y notas clínicas que puedes usar para tus registros.</p>
  </div>

  <form id="formulario-grabacion" class="scribe-card">
    <div class="form-row">
      <div class="form-input">
        <label for="paciente">Nombre del Paciente</label>
        <input type="text" id="paciente" name="paciente" placeholder="Ej. Juan Pérez" required>
      </div>

      <div class="form-input">
        <label for="plantilla">Plantilla</label>
        <select id="plantilla" name="plantilla" required>
          <option value="">Seleccionar</option>
          <option value="soap-examen">SOAP con examen físico</option>
          <option value="soap-simple">SOAP simple</option>
          <option value="resumen">Resumen libre</option>
        </select>
      </div>

      <button type="button" id="btn-visita" class="btn-iniciar-visita">
        <i class="fas fa-plus"></i> Iniciar Visita
      </button>
    </div>

    <hr class="separador">

    <div id="bloqueGrabacion" class="grabacion-contenedor" style="display: none;">
      <h2 style="text-align: center;">Capturar Grabación</h2>

      <div style="display: flex; justify-content: center; margin-top: 24px;">
        <button type="button" id="btn-grabacion" class="boton-circular inactivo">
          <div id="estadoTexto">Iniciar grabación</div>
          <div id="cronometro" style="font-size: 16px; font-weight: 500; margin-top: 4px;">00:00</div>
          <div id="iconoGrabacion" style="font-size: 24px; margin-top: 6px;">
            <i class="fas fa-microphone"></i>
          </div>
        </button>
      </div>

      <div id="estadoGrabacion" class="alerta-info" style="margin-top: 24px;"></div>

      <audio id="audio-reproducir" controls hidden class="reproductor-audio" style="display: none;"></audio>

      <progress id="barraProgreso" value="0" max="100" style="width: 100%; display: none; margin-top: 16px;"></progress>

      <button type="button" id="btn-subir" class="btn-subir" style="margin-top: 16px; display: none;">Subir Grabación</button>
    </div>
  </form>
</div>

<div id="modal-consentimiento" class="modal-consentimiento">
  <div class="modal-contenido">
    <div class="modal-izquierda">
      <div class="modal-icono"><i class="fas fa-exclamation-triangle"></i></div>
      <h2>Consentimiento requerido</h2>
      <p>
        Esta grabación requiere consentimiento verbal. Asegúrate que todos estén informados.
        <strong>(La confirmación quedará registrada)</strong>
      </p>
      <div class="modal-botones">
        <button id="btn-cancelar" class="btn-cancelar">Cancelar</button>
        <button id="btn-aceptar" class="btn-confirmar">Aceptar y Continuar</button>
      </div>
    </div>
    <div class="modal-derecha">
      <img src="{{ url_for('static', filename='img/Banner-Doctor.png') }}" alt="Doctora salud digital">
    </div>
  </div>
</div>

<script>
  let mediaRecorder, audioChunks = [];
  let isRecording = false, isPaused = false;
  let cronometroInterval, tiempoGrabado = 0;

  document.addEventListener('DOMContentLoaded', () => {
    const modal = document.getElementById('modal-consentimiento');
    const btnVisita = document.getElementById('btn-visita');
    const btnCancelar = document.getElementById('btn-cancelar');
    const btnAceptar = document.getElementById('btn-aceptar');
    const bloqueGrabacion = document.getElementById('bloqueGrabacion');

    btnVisita.addEventListener('click', () => {
      const paciente = document.getElementById('paciente').value.trim();
      const plantilla = document.getElementById('plantilla').value;
      if (!paciente || !plantilla) {
        alert("Por favor, completa todos los campos.");
        return;
      }
      modal.style.display = 'flex';
    });

    btnCancelar.onclick = () => modal.style.display = 'none';
    btnAceptar.onclick = () => {
      modal.style.display = 'none';
      bloqueGrabacion.style.display = 'block';
    };
  });

  function formatearTiempo(seg) {
    const m = String(Math.floor(seg / 60)).padStart(2, '0');
    const s = String(seg % 60).padStart(2, '0');
    return `${m}:${s}`;
  }

  document.getElementById("btn-grabacion").addEventListener("click", async function () {
    const btn = this;
    const estadoTexto = document.getElementById("estadoTexto");
    const icono = document.getElementById("iconoGrabacion");
    const cronometro = document.getElementById("cronometro");
    const estado = document.getElementById("estadoGrabacion");
    const audio = document.getElementById("audio-reproducir");
    const btnSubir = document.getElementById("btn-subir");

    if (!isRecording) {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream);
        audioChunks = [];
        tiempoGrabado = 0;
        cronometro.innerText = "00:00";

        mediaRecorder.ondataavailable = e => audioChunks.push(e.data);
        mediaRecorder.onstop = () => {
          const audioBlob = new Blob(audioChunks, { type: "audio/webm" });
          audio.src = URL.createObjectURL(audioBlob);
          audio.hidden = false;
          audio.style.display = 'block';
          btnSubir.disabled = false;
          btnSubir.style.display = 'inline-block';
          estado.innerText = "✅ Grabación finalizada.";
          clearInterval(cronometroInterval);
        };

        mediaRecorder.start();
        cronometroInterval = setInterval(() => {
          tiempoGrabado++;
          cronometro.innerText = formatearTiempo(tiempoGrabado);
        }, 1000);

        isRecording = true;
        btn.classList.remove("inactivo");
        btn.classList.add("activo");
        estadoTexto.innerText = "Finalizar grabación";
        icono.innerHTML = '<i class="fas fa-stop"></i>';
        estado.innerText = "🔴 Grabando...";

      } catch (err) {
        console.error(err);
        alert("No se pudo acceder al micrófono.");
      }
    } else {
      mediaRecorder.stop();
      isRecording = false;
      estadoTexto.innerText = "Iniciar grabación";
      icono.innerHTML = '<i class="fas fa-microphone"></i>';
      btn.classList.remove("activo");
      btn.classList.add("inactivo");
    }
  });

  document.getElementById("btn-subir").addEventListener("click", async () => {
    const paciente = document.getElementById('paciente').value;
    const plantilla = document.getElementById('plantilla').value;
    const audioBlob = new Blob(audioChunks, { type: "audio/webm" });
    const formData = new FormData();
    formData.append("audio", audioBlob, "grabacion.webm");
    formData.append("paciente", paciente);
    formData.append("plantilla", plantilla);

    const estado = document.getElementById("estadoGrabacion");
    const barra = document.getElementById("barraProgreso");
    barra.style.display = 'block';
    barra.value = 0;
    estado.innerText = "⏳ Subiendo grabación...";

    try {
      const response = await fetch("/procesar_grabacion", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        let errorText = `Error al subir la grabación: Código ${response.status}`;
        try {
          const errorJson = await response.json();
          if (errorJson && errorJson.error) {
            errorText = `Error al subir la grabación: ${errorJson.error}`;
          } else {
            const textResponse = await response.text();
            if (textResponse) {
              errorText = `Error al subir la grabación: ${textResponse}`;
            }
          }
        } catch (e) {
          console.error("Error al parsear la respuesta de error:", e);
        }
        console.error(`Error al procesar la grabación: ${response.status} - ${errorText}`);
        estado.innerText = `❌ ${errorText}`;
        barra.style.display = 'none';
      } else {
        console.log("Grabación procesada exitosamente.");
        estado.innerText = "✅ Grabación subida y procesada. Redirigiendo al historial...";
        barra.style.display = 'none';
        window.location.href = "/historial_visitas";
      }

    } catch (error) {
      console.error("Error de red al subir la grabación:", error);
      estado.innerText = "❌ Error de red al subir la grabación.";
      barra.style.display = 'none';
    }
  });
</script>

{% endblock %}
    