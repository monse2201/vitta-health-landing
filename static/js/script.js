document.addEventListener("DOMContentLoaded", function () {
    const sendButton = document.querySelector(".send-btn");
    const messageInput = document.querySelector(".chat-input input");
    const chatMessages = document.querySelector(".chat-messages");
    const chatItems = document.querySelectorAll(".chat-item");
    const chatHeader = document.querySelector(".chat-header h3"); // Asegúrate de que existe este elemento en tu HTML

    function sendMessage() {
        let messageText = messageInput.value.trim();
        if (messageText !== "") {
            const newMessage = document.createElement("div");
            newMessage.classList.add("message", "sent");
            newMessage.innerHTML = `
                ${messageText} 
                <br><small>${new Date().toLocaleTimeString()}</small>
            `;

            chatMessages.appendChild(newMessage);
            messageInput.value = "";
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }
    }

    // Evento de clic en el botón de enviar
    if (sendButton) {
        sendButton.addEventListener("click", sendMessage);
    }

    // Evento para presionar "Enter" y enviar mensaje
    if (messageInput) {
        messageInput.addEventListener("keypress", function (event) {
            if (event.key === "Enter") {
                event.preventDefault(); // Evita salto de línea en input
                sendMessage();
            }
        });
    }

    // Simulación de un mensaje recibido después de 3 segundos
    setTimeout(() => {
        const receivedMessage = document.createElement("div");
        receivedMessage.classList.add("message", "received");
        receivedMessage.innerHTML = `
            Hola, soy un asistente automático.
            <br><small>${new Date().toLocaleTimeString()}</small>
        `;
        chatMessages.appendChild(receivedMessage);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }, 3000);

    // Manejo del cambio de chat
    chatItems.forEach((item) => {
        item.addEventListener("click", function () {
            const chatName = this.querySelector("h4").innerText;
            if (chatHeader) {
                chatHeader.innerText = chatName;
            }
        });
    });

    // Manejo de búsqueda en la tabla de pacientes
    const pacientes = [
        { nombre: "Abue 🧓❤️", telefono: "50683097495", email: "abue@example.com", ultimo_mensaje: "02 Feb, 2025", primer_mensaje: "24 Ene, 2025", estado: "En Tratamiento", proxima_accion: "Consulta el 10 Feb" },
        { nombre: "Andrea 😍", telefono: "50687011234", email: "andrea@example.com", ultimo_mensaje: "01 Feb, 2025", primer_mensaje: "15 Ene, 2025", estado: "Alta Médica", proxima_accion: "Recordatorio de seguimiento" }
    ];

    const searchInput = document.getElementById("search");
    if (searchInput) {
        searchInput.addEventListener("input", function (e) {
            const value = e.target.value.toLowerCase();
            const rows = document.querySelectorAll(".patients-table tbody tr");

            rows.forEach(row => {
                const name = row.cells[1].textContent.toLowerCase();
                row.style.display = name.includes(value) ? "" : "none";
            });
        });
    }

    // Función para agregar respuestas automáticas
    function agregarRespuesta() {
        let input = document.getElementById("nuevaRespuesta");
        let texto = input.value.trim();

        if (texto !== "") {
            let lista = document.getElementById("listaRespuestas");
            let item = document.createElement("li");
            item.textContent = texto;
            lista.appendChild(item);
            input.value = ""; // Limpiar input
        } else {
            alert("Por favor, escribe una respuesta.");
        }
    }

    // Función para agregar recordatorios
    function agregarRecordatorio() {
        let input = document.getElementById("nuevoRecordatorio");
        let texto = input.value.trim();

        if (texto !== "") {
            let lista = document.getElementById("listaRecordatorios");
            let item = document.createElement("li");
            item.textContent = texto;
            lista.appendChild(item);
            input.value = ""; // Limpiar input
        } else {
            alert("Por favor, escribe un recordatorio.");
        }
    }

    // Asignar eventos a botones si existen en el DOM
    const btnAgregarRespuesta = document.getElementById("btnAgregarRespuesta");
    if (btnAgregarRespuesta) {
        btnAgregarRespuesta.addEventListener("click", agregarRespuesta);
    }

    const btnAgregarRecordatorio = document.getElementById("btnAgregarRecordatorio");
    if (btnAgregarRecordatorio) {
        btnAgregarRecordatorio.addEventListener("click", agregarRecordatorio);
    }

    // Manejo de eliminación y edición de tareas
    document.querySelectorAll(".delete-btn").forEach(button => {
        button.addEventListener("click", function () {
            alert("Eliminar tarea no implementado aún");
        });
    });

    document.querySelectorAll(".edit-btn").forEach(button => {
        button.addEventListener("click", function () {
            alert("Editar tarea no implementado aún");
        });
    });
});



