function downloadProjectPDF(projectId) {
    const proyecto = typeof proyectos !== 'undefined' ? proyectos.find(p => p.id === projectId) : null;
    if (!proyecto) return;

    const printWin = window.open('', '_blank');
    if (!printWin) {
        if (typeof showToast === 'function') {
            showToast('Habilite las ventanas emergentes para descargar el PDF', 'warning');
        } else {
            alert('Habilite las ventanas emergentes para descargar el PDF');
        }
        return;
    }

    const printContentElement = document.getElementById('viewProjectDetails');
    if (!printContentElement) return;

    // Clone and clean up node if necessary
    const sheet = printContentElement.cloneNode(true);
    sheet.querySelectorAll('.no-print').forEach(el => el.remove());

    const content = sheet.outerHTML;

    const html = `<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Informe Analítico - ${proyecto.nombre || ''}</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body { background: white; padding: 40px; font-family: 'Outfit', sans-serif; }
        .modal-footer { display: none !important; }
        .close-btn { display: none !important; }
        .shadow-sm, .shadow-lg, .shadow-premium { box-shadow: none !important; border-color: #e2e8f0; border-width: 1px; }
        .custom-scrollbar::-webkit-scrollbar { display: none; }
        * { print-color-adjust: exact; -webkit-print-color-adjust: exact; }
        @media print {
            @page { margin: 10mm; size: A3 portrait; }
        }
        .max-w-4xl { max-width: 64rem; margin-left: auto; margin-right: auto; }
    </style>
</head>
<body onload="setTimeout(function() { window.print(); setTimeout(function() { window.close(); }, 500); }, 1500);">
    <div class="max-w-4xl mx-auto">
        <div style="margin-bottom: 2rem; border-bottom: 4px solid #4f46e5; padding-bottom: 1rem;">
            <h1 style="color: #4f46e5; font-size: 2rem; font-weight: 800; margin: 0;">Informe Analítico de Proyecto</h1>
            <p style="color: #64748b; font-size: 0.875rem; margin-top: 0.5rem; text-transform: uppercase; font-weight: 700; letter-spacing: 0.1em;">${proyecto.nombre || 'Exportación de Auditoría'}</p>
        </div>
        ${content}
    </div>
</body>
</html>`;

    printWin.document.open();
    printWin.document.write(html);
    printWin.document.close();
}
