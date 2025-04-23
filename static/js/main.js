document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('researchForm');
    const loading = document.getElementById('loading');
    const result = document.getElementById('result');
    const resultContent = document.getElementById('resultContent');
    const error = document.getElementById('error');
    const errorMessage = document.getElementById('errorMessage');

    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        // Get form data
        const topic = document.getElementById('topic').value;
        const format = document.getElementById('format').value;

        // Show loading state
        loading.classList.remove('hidden');
        result.classList.add('hidden');
        error.classList.add('hidden');

        try {
            // Make API request
            const response = await fetch('/research', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ topic, format }),
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Failed to get research results');
            }

            // Show results
            resultContent.textContent = data.result;
            result.classList.remove('hidden');
        } catch (err) {
            // Show error
            errorMessage.textContent = err.message;
            error.classList.remove('hidden');
        } finally {
            // Hide loading state
            loading.classList.add('hidden');
        }
    });
}); 
