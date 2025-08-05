// Define el tour y sus pasos.
const tour = new Shepherd.Tour({
    use  Defaults: true,
    defaultStepOptions: {
        cancelIcon: { enabled: true }
    }
});

// Paso 1: Un ejemplo en la página principal
tour.addStep({
    id: 'primer-paso-home',
    text: '¡Bienvenido! Este es el botón principal para iniciar un nuevo proyecto.',
    attachTo: {
        element: '#boton-crear-home',
        on: 'bottom'
    }
});

// Paso 2: Un ejemplo en otra página
tour.addStep({
    id: 'segundo-paso-perfil',
    text: 'Aquí puedes editar la información de tu perfil.',
    attachTo: {
        element: '#boton-editar-perfil',
        on: 'top'
    }
});