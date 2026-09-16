export function updateStepper(stepNumber) {
    [1, 2, 3, 4].forEach((number) => {
        const element = document.getElementById(`step-${number}-btn`);
        if (!element) return;
        element.classList.toggle('active', number === stepNumber);
        element.classList.toggle('completed', number < stepNumber);
    });
}
