// Polyfill for crypto.randomUUID in insecure contexts (HTTP)
if (typeof crypto === 'undefined') {
  // @ts-ignore
  window.crypto = {};
}
if (typeof crypto.randomUUID !== 'function') {
  // @ts-ignore
  crypto.randomUUID = function() {
    return "10000000-1000-4000-8000-100000000000".replace(/[018]/g, (c: any) =>
        (c ^ (Math.random() * 16) >> c / 4).toString(16)
    );
  };
}
