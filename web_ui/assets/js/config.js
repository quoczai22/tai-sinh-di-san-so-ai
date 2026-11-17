(function initApiBase() {
    const params = new URLSearchParams(window.location.search);
    const override = params.get('api') || window.localStorage?.getItem('DH_API_BASE');
    window.DH_API_BASE = window.DH_API_BASE || override || '/api';
})();
