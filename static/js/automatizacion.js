document.addEventListener("DOMContentLoaded", function () {
    const btnRespuestasRapidas = document.getElementById("btn-respuestas-rapidas");
    const btnCrearNueva = document.getElementById("btn-crear-nueva");
    const formRespuestas = document.getElementById("form-respuestas");
    const listaRespuestas = document.getElementById("lista-respuestas");
    const nombreRespuesta = document.getElementById("nombre-respuesta");
    const mensajeRapido = document.getElementById("mensaje-rapido");
    const guardarRespuesta = document.getElementById("guardar-respuesta");
    const vistaPreviaChat = document.getElementById("vista-previa-chat");

    let modoEdicion = false;
    let indexEdicion = null;

    // Verificar si el botón 'Crear Nueva' existe
    if (btnCrearNueva) {
        btnCrearNueva.addEventListener("click", function () {
            console.log("🛠️ Botón 'Crear Nueva' fue presionado.");
            formRespuestas.classList.add("show"); // Mostrar el formulario
            listaRespuestas.classList.remove("show"); // Ocultar la lista de respuestas
            // Limpiar el formulario
            nombreRespuesta.value = ""; // Limpiar el campo de nombre
            mensajeRapido.value = ""; // Limpiar el campo de mensaje
            modoEdicion = false; // Asegurarse de que no esté en modo edición
        });
    } else {
        console.error("❌ Error: No se encontró el botón 'btn-crear-nueva'.");
    }

    // Función para mostrar la lista de respuestas guardadas
    function toggleForm(formToShow) {
        formRespuestas.classList.remove("show");
        listaRespuestas.classList.remove("show");

        if (formToShow) {
            formToShow.classList.add("show");
        }
    }

    // Mostrar lista de respuestas guardadas
    btnRespuestasRapidas.addEventListener("click", function () {
        toggleForm(listaRespuestas);
        cargarRespuestas();
    });

    // Cargar respuestas desde la API
    function cargarRespuestas() {
        fetch('/api/respuestas_rapidas')
            .then(response => {
                if (!response.ok) {
                    return response.text().then(text => { throw new Error(text); });
                }
                return response.json();
            })
            .then(data => {
                const respuestasGuardadas = document.getElementById("respuestas-guardadas");

                if (!respuestasGuardadas) {
                    console.error("❌ Error: No se encontró el contenedor 'respuestas-guardadas'.");
                    return;
                }

                respuestasGuardadas.innerHTML = ""; // Limpiar contenido anterior

                if (!data.respuestas || data.respuestas.length === 0) {
                    respuestasGuardadas.innerHTML = "<p>No hay respuestas guardadas.</p>";
                } else {
                    data.respuestas.forEach(respuesta => {
                        let li = document.createElement("li");
                        li.innerHTML = `
                            <strong>${respuesta.nombre}</strong> 
                            <p>${respuesta.mensaje}</p>
                            <button class="btn-editar" data-id="${respuesta.id}">✏️ Editar</button>
                            <button class="btn-eliminar" data-id="${respuesta.id}">🗑️ Eliminar</button>
                        `;
                        respuestasGuardadas.appendChild(li);
                    });
                }
                agregarEventosBotones(); // Agregar eventos a los botones después de cargar las respuestas
            })
            .catch(error => console.error("❌ Error al cargar respuestas:", error));
    }

    // Agregar eventos a los botones de editar y eliminar
    function agregarEventosBotones() {
        // Botón editar
        document.querySelectorAll(".btn-editar").forEach(button => {
            button.addEventListener("click", function () {
                const id = this.getAttribute("data-id");
                fetch(`/api/respuesta/${id}`)
                    .then(response => response.json())
                    .then(data => {
                        nombreRespuesta.value = data.nombre;
                        mensajeRapido.value = data.mensaje;
                        guardarRespuesta.setAttribute("data-id", id);
                        formRespuestas.classList.add("show");
                        modoEdicion = true; // Cambiar a modo edición
                        indexEdicion = id; // Guardar el ID para la edición
                    })
                    .catch(error => console.error("❌ Error al cargar respuesta:", error));
            });
        });

        // Botón eliminar
        document.querySelectorAll(".btn-eliminar").forEach(button => {
            button.addEventListener("click", function () {
                const id = this.getAttribute("data-id");
                console.log("🛠️ Intentando eliminar mensaje con ID:", id);
                if (!id || isNaN(id)) {
                    alert("❌ Error: ID inválido.");
                    return;
                }
                eliminarRespuesta(id);
            });
        });
    }

    // Función para eliminar una respuesta rápida
    function eliminarRespuesta(id) {
        console.log("🛠️ Intentando eliminar respuesta con ID:", id);

        if (confirm("¿Estás seguro de que deseas eliminar esta respuesta rápida?")) {
            fetch(`/api/eliminar_respuesta/${id}`, {
                method: "DELETE"
            })
            .then(response => {
                if (!response.ok) {
                    return response.json().then(error => { throw new Error(error.error); });
                }
                alert("✅ Respuesta eliminada con éxito");
                cargarRespuestas(); // Recargar la lista después de eliminar
            })
            .catch(error => {
                console.error("❌ Error al eliminar respuesta:", error);
                alert("❌ " + error.message);
            });
        }
    }

    // Inicializar el nombre de la respuesta
    fetch('/api/respuestas_rapidas')
    .then(response => response.json())
    .then(data => {
        if (!data.respuestas || !Array.isArray(data.respuestas)) {
            console.error("❌ Error: Respuesta inválida de la API.");
            nombreRespuesta.value = "Respuesta Rápida 1"; // Valor predeterminado si hay un error
            return;
        }
        const numero = data.respuestas.length + 1;
        nombreRespuesta.value = `Respuesta Rápida ${numero}`;
    })
    .catch(error => {
        console.error("❌ Error al obtener respuestas rápidas:", error);
        nombreRespuesta.value = "Respuesta Rápida 1"; // Valor predeterminado si hay un error
    });

    // Actualizar la vista previa del chat
    function actualizarVistaPrevia(mensaje) {
        if (!vistaPreviaChat) {
            console.error("❌ Error: No se encontró el contenedor de vista previa.");
            return;
        }

        vistaPreviaChat.innerHTML = `
            <div class="mensaje-chat">
                <div class="usuario">👤 Usuario:</div>
                <div class="mensaje">Hola, ¿puedes ayudarme?</div>
            </div>
            <div class="mensaje-chat">
                <div class="bot">🤖 Bot:</div>
                <div class="mensaje">${mensaje || "Aquí aparecerá tu respuesta rápida..."}</div>
            </div>
        `;
    }

    // Escuchar cambios en el textarea para actualizar la vista previa
    mensajeRapido.addEventListener("input", function () {
        actualizarVistaPrevia(this.value);
    });

    // Guardar nueva respuesta o actualizar existente
    guardarRespuesta.addEventListener("click", function () {
        const nuevaRespuesta = {
            nombre: nombreRespuesta.value.trim(),
            mensaje: mensajeRapido.value.trim()
        };

        if (!nuevaRespuesta.mensaje) {
            alert("⚠️ El mensaje no puede estar vacío.");
            return;
        }

        let url = "/api/guardar_respuesta";
        let method = "POST";

        if (modoEdicion) {
            url = `/api/editar_respuesta/${indexEdicion}`;
            method = "PUT";
        }

        fetch(url, {
            method: method,
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(nuevaRespuesta)
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert(`❌ Error: ${data.error}`);
            } else {
                alert("✅ Respuesta guardada correctamente");
                formRespuestas.classList.remove("show");
                cargarRespuestas();  // Recargar la lista sin recargar la página
                modoEdicion = false;
                indexEdicion = null;
            }
        })
        .catch(error => console.error("❌ Error al guardar respuesta:", error));
    });

    // Funcionalidad para programar mensajes
    const scheduleModal = document.getElementById("scheduledMessageModal");
    const scheduleMessageBtn = document.getElementById("scheduleMessageBtn");

    // Abrir modal al hacer clic en "Programar mensaje"
    document.querySelector(".chat-action-btn.schedule-message-btn").addEventListener("click", function () {
        scheduleModal.style.display = "flex";
    });

    // Cerrar modal
    document.querySelector(".close-modal-btn").addEventListener("click", function () {
        scheduleModal.style.display = "none";
    });

    // Guardar mensaje programado
    scheduleMessageBtn.addEventListener("click", function () {
        const date = document.getElementById("scheduled-date").value;
        const time = document.getElementById("scheduled-time").value;
        const message = document.getElementById("scheduled-message").value.trim();

        if (!date || !time || !message) {
            alert("⚠️ Todos los campos son obligatorios.");
            return;
        }

        fetch("/api/programar_mensaje", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ date, time, message })
        })
        .then(response => response.json())
        .then(data => {
            alert("✅ Mensaje programado correctamente");
            scheduleModal.style.display = "none";
            cargarMensajesProgramados(); // Recargar la lista de mensajes programados
        })
        .catch(error => console.error("❌ Error al programar mensaje:", error));
    });

    // Cargar mensajes programados al iniciar la página
    cargarMensajesProgramados();

    // Conectar WebSocket
    var socket = io.connect(window.location.origin);

    // Escuchar el evento cuando un mensaje programado se envía
    socket.on("mensaje_enviado", function (data) {
        agregarMensajeAConversacion(data);
    });

    // Función para agregar el mensaje enviado al chat
    function agregarMensajeAConversacion(data) {
        const chatMessages = document.querySelector(".chat-messages");

        let nuevoMensaje = `
            <div class="message sent">
                <p>${data.mensaje}</p>
                <span class="time">${data.fecha}</span>
            </div>
        `;

        chatMessages.insertAdjacentHTML("beforeend", nuevoMensaje);
        chatMessages.scrollTop = chatMessages.scrollHeight;  // Hacer scroll al final
    }

    // Función para abrir el modal de edición con los datos actuales
    function editarMensajeProgramado(id) {
        fetch(`/api/mensaje_programado/${id}`)
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    alert("❌ Error: " + data.error);
                    return;
                }

                // Llenar el modal con los datos obtenidos
                document.getElementById("editar-mensaje-id").value = data.id;
                document.getElementById("editar-mensaje-texto").value = data.mensaje;
                document.getElementById("editar-mensaje-fecha").value = convertirFechaParaInput(data.fecha);

                // Mostrar el modal
                document.getElementById("modal-editar-mensaje").style.display = "block";
            })
            .catch(error => console.error("❌ Error al obtener el mensaje:", error));
    }

    function guardarEdicionMensaje() {
        const id = document.getElementById("editar-mensaje-id").value;
        const mensaje = document.getElementById("editar-mensaje-texto").value.trim();
        const fecha = document.getElementById("editar-mensaje-fecha").value;

        if (!mensaje || !fecha) {
            alert("⚠️ Todos los campos son obligatorios.");
            return;
        }

        fetch(`/api/editar_mensaje_programado/${id}`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ mensaje, fecha })
        })
        .then(response => response.json())
        .then(() => {
            alert("✅ Mensaje editado con éxito");
            cerrarModalEditar();
            cargarMensajesProgramados();
        })
        .catch(error => console.error("❌ Error al editar mensaje:", error));
    }

    // Función auxiliar para convertir fechas a formato "YYYY-MM-DDTHH:MM" para el input de tipo datetime-local
    function convertirFechaParaInput(fecha) {
        const partes = fecha.split(" ");
        const [dia, mes, año] = partes[0].split("/");
        const [hora, minuto] = partes[1].split(":");
        return `${año}-${mes}-${dia}T${hora}:${minuto}`;
    }

    // Cargar mensajes programados
    function cargarMensajesProgramados() {
        fetch('/api/mensajes_programados')
            .then(response => response.json())
            .then(data => {
                const contenedor = document.getElementById("lista-mensajes-programados");
                contenedor.innerHTML = "";

                if (data.length === 0) {
                    contenedor.innerHTML = "<p>No hay mensajes programados.</p>";
                } else {
                    data.forEach(mensaje => {
                        let mensajeHTML = `
                            <div class="mensaje-programado" id="mensaje-programado-${mensaje.id}">
                                <p><strong>${mensaje.contacto}</strong></p>
                                <p>${mensaje.mensaje}</p>
                                <p><small>${mensaje.fecha}</small></p>
                                <button class="btn-editar" onclick="editarMensajeProgramado(${mensaje.id})">✏️ Editar</button>
                                <button class="btn-eliminar" onclick="eliminarMensajeProgramado(${mensaje.id})">🗑️ Eliminar</button>
                            </div>
                        `;
                        contenedor.insertAdjacentHTML("beforeend", mensajeHTML);
                    });
                }
            })
            .catch(error => console.error("❌ Error al cargar mensajes programados:", error));
    }
});