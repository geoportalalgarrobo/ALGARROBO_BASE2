        let proyectos = [];
        let catalogData = {
            areas: [],
            financiamientos: [],
            estados_proyecto: [],
            etapas_proyecto: [],
            estados_postulacion: [],
            sectores: [],
            lineamientos_estrategicos: []
        };
        let editingId = null;
        let columnsVisible = false;

        const currentFilters = { area: [], lineamiento: [], financiamiento: [], anno_elaboracion: [], anno_ejecucion: [], estado: [], etapa: [], estado_postulacion: [], profesional: [] };
        const mapFilters = { area: 'area_nombre', lineamiento: 'lineamiento_estrategico_nombre', financiamiento: 'financiamiento_nombre', anno_elaboracion: 'anno_elaboracion', anno_ejecucion: 'anno_ejecucion', estado: 'estado_nombre', etapa: 'etapa_nombre', estado_postulacion: 'estado_postulacion_nombre', profesional: 'profesional_1' };
        const labelFilters = { area: 'Ãrea', lineamiento: 'LÃ­nea', financiamiento: 'Fte.', anno_elaboracion: 'Elab.', anno_ejecucion: 'Ejec.', estado: 'Estado', etapa: 'Etapa', estado_postulacion: 'Post.', profesional: 'Prof.' };
        let activeMenuKey = null;

        async function loadCatalogData() {
            try {
                const resources = [
                    'areas', 'financiamientos', 'estados_proyecto',
                    'etapas_proyecto', 'estados_postulacion', 'sectores',
                    'lineamientos_estrategicos'
                ];

                const results = await Promise.all(
                    resources.map(res => api.get(`/${res}`).catch(() => []))
                );

                resources.forEach((res, index) => {
                    catalogData[res] = results[index].sort((a, b) =>
                        (a.nombre || '').localeCompare(b.nombre || '')
                    );
                });

                populateFormSelects();
                populateFilterSelects();
            } catch (error) {
                console.error('Error cargando catÃ¡logos:', error);
                showToast('Error al sincronizar datos', 'error');
            }
        }

        function populateFilterSelects() {
            // Reemplazado por el nuevo manejo dinÃ¡mico populateFilters() alv
        }

        function populateFormSelects() {
            const fillSelect = (elementId, data, defaultText, displayFn = null) => {
                const select = document.getElementById(elementId);
                if (!select) return;

                const currentVal = select.value;

                select.innerHTML = `<option value="">${defaultText}</option>`;
                data.forEach(item => {
                    const option = document.createElement('option');
                    option.value = item.id;
                    option.textContent = displayFn ? displayFn(item) : item.nombre;
                    select.appendChild(option);
                });

                if (currentVal) select.value = currentVal;
            };

            fillSelect('area_id', catalogData.areas, 'Seleccione Ãrea');
            fillSelect('financiamiento_id', catalogData.financiamientos, 'Seleccione Financiamiento', (i) => i.fuente || i.nombre);
            fillSelect('estado_proyecto_id', catalogData.estados_proyecto, 'Seleccione Estado');
            fillSelect('etapa_proyecto_id', catalogData.etapas_proyecto, 'Seleccione Etapa');
            fillSelect('estado_postulacion_id', catalogData.estados_postulacion, 'Seleccione Estado PostulaciÃ³n');
            fillSelect('sector_id', catalogData.sectores, 'Seleccione Sector');
            fillSelect('lineamiento_estrategico_id', catalogData.lineamientos_estrategicos, 'Seleccione Lineamiento');
        }

        function formatDateForInput(dateString) {
            if (!dateString) return '';
            if (typeof dateString === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(dateString)) {
                return dateString;
            }
            const dateObj = new Date(dateString);
            if (isNaN(dateObj.getTime())) return dateString;
            const year = dateObj.getFullYear();
            const month = String(dateObj.getMonth() + 1).padStart(2, '0');
            const day = String(dateObj.getDate()).padStart(2, '0');
            return `${year}-${month}-${day}`;
        }

        function formatDisplayDate(dateString) {
            if (!dateString) return '-';
            try {
                const date = new Date(dateString);
                return date.toLocaleDateString('es-CL', {
                    year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit'
                });
            } catch (e) {
                return dateString;
            }
        }

        document.addEventListener('DOMContentLoaded', function () {
            checkLoginStatus();

            loadCatalogData().then(() => {
                loadProjects().then(() => {
                    handleAuditParams();
                });
            });

            const searchInput = document.getElementById('searchInput');
            if (searchInput) {
                searchInput.addEventListener('input', applyFilters);
            }
            document.getElementById('proyectoForm').addEventListener('submit', handleSubmit);

            // Cerrar menÃº de filtros al hacer click fuera
            window.onclick = (e) => {
                const target = e.target;
                if (!target.closest('.group') && !target.closest('.relative')) {
                    document.querySelectorAll('[id^="menu-"]').forEach(m => m.classList.add('hidden'));
                    activeMenuKey = null;
                }
            };
        });

        async function loadProjects() {
            try {
                const tableBody = document.getElementById('projectsTableBody');
                tableBody.innerHTML = `
                    <tr>
                        <td colspan="8" class="text-center py-12">
                            <div class="flex flex-col items-center justify-center">
                                <div class="animate-spin rounded-full h-10 w-10 border-b-2 border-indigo-600 mb-4"></div>
                                <p class="text-gray-500 font-medium">Cargando proyectos...</p>
                            </div>
                        </td>
                    </tr>
                `;

                proyectos = await api.get('/proyectos');

                proyectos.sort((a, b) => {
                    const dateA = new Date(a.fecha_actualizacion || a.fecha_postulacion || 0);
                    const dateB = new Date(b.fecha_actualizacion || b.fecha_postulacion || 0);
                    const diff = dateB - dateA;
                    if (diff !== 0) return diff;
                    return (a.nombre || '').localeCompare(b.nombre || '');
                });

                applyFilters();

                const today = new Date();
                const formattedDate = today.toLocaleDateString('es-ES', {
                    day: '2-digit', month: '2-digit', year: 'numeric'
                });
                document.getElementById('lastUpdate').textContent = formattedDate;
            } catch (error) {
                console.error('Error:', error);
                showToast('Error al cargar los proyectos', 'error');
            }
        }

        function populateFilters() {
            const rib = document.getElementById('filterRibbon');
            if (!rib) return;
            
            // Build the standard ribbon view
            rib.innerHTML = Object.keys(mapFilters).map(key => {
                const count = currentFilters[key].length;
                const label = count === 0 ? labelFilters[key] : `${labelFilters[key]}: ${count}`;
                const isActive = count > 0;
                
                // Check if this menu was open
                const isMenuOpen = activeMenuKey === key;

                return `
                    <div class="relative">
                        <button type="button" onclick="toggleFilterMenu('${key}', event)" class="px-5 py-2.5 rounded-2xl border-2 ${isActive ? 'bg-indigo-600 text-white border-indigo-600 shadow-md shadow-indigo-200' : 'bg-white text-slate-500 border-slate-100 hover:border-slate-300 hover:text-slate-700'} text-[10px] font-black uppercase tracking-widest flex items-center gap-3 transition-all">
                            <i class="fas fa-filter text-[10px] ${isActive ? 'text-white' : 'text-slate-400'}"></i> ${label}
                            <i class="fas fa-chevron-down text-[10px] opacity-40 ml-1"></i>
                        </button>
                        <div id="menu-${key}" class="${isMenuOpen ? '' : 'hidden'} absolute top-full left-0 mt-3 w-72 bg-white border border-slate-200 shadow-2xl rounded-2xl z-[5000] p-4 max-h-[400px] overflow-y-auto scrollbar-thin ring-1 ring-black ring-opacity-5">
                            ${renderFilterOptions(key)}
                        </div>
                    </div>
                `;
            }).join('');
            
            // Re-apply focus or open state if needed
            if (activeMenuKey) {
                const menu = document.getElementById(`menu-${activeMenuKey}`);
                if (menu) menu.classList.remove('hidden');
            }
        }

        function renderFilterOptions(key) {
            const dataKey = mapFilters[key];
            const opts = [...new Set(proyectos.map(p => String(p[dataKey] || '').trim()).filter(Boolean))].sort();
            const curr = currentFilters[key];

            return `
                <div class="space-y-1">
                    <label class="flex items-center gap-3 p-2 hover:bg-slate-50 rounded-lg cursor-pointer border-b border-slate-100 pb-2 mb-1">
                        <input type="checkbox" onchange="applyBulkFilter('${key}', this)" ${curr.length === 0 ? 'checked' : ''} class="w-4 h-4 accent-indigo-600">
                        <span class="text-[10px] font-black text-indigo-600 uppercase">-- TODAS --</span>
                    </label>
                    ${opts.map(o => `
                        <label class="flex items-center gap-3 p-2 hover:bg-slate-50 rounded-lg cursor-pointer group">
                            <input type="checkbox" value="${o}" onchange="updateFilter('${key}', this)" ${curr.includes(o) ? 'checked' : ''} class="w-4 h-4 accent-indigo-600">
                            <span class="text-xs font-bold text-slate-700 group-hover:text-indigo-600 transition-colors">${o}</span>
                        </label>
                    `).join('')}
                </div>
            `;
        }

        function toggleFilterMenu(key, e) {
            if (e) e.stopPropagation();
            const el = document.getElementById(`menu-${key}`);
            if (!el) return;
            const wasOpen = !el.classList.contains('hidden');
            document.querySelectorAll('[id^="menu-"]').forEach(m => m.classList.add('hidden'));
            
            if (!wasOpen) {
                el.classList.remove('hidden');
                activeMenuKey = key;
            } else {
                activeMenuKey = null;
            }
        }

        function applyBulkFilter(key, el) { if (el.checked) currentFilters[key] = []; applyFilters(); }

        function updateFilter(key, el) {
            const val = el.value;
            if (el.checked) currentFilters[key].push(val);
            else currentFilters[key] = currentFilters[key].filter(v => v !== val);
            applyFilters();
        }

        function limpiarFiltros() {
            Object.keys(currentFilters).forEach(k => currentFilters[k] = []);
            const searchInput = document.getElementById('searchInput');
            if (searchInput) searchInput.value = '';
            activeMenuKey = null;
            applyFilters();
        }

        function applyFilters() {
            const searchInput = document.getElementById('searchInput');
            const term = searchInput ? searchInput.value.toLowerCase() : '';

            const filteredData = proyectos.filter(p => {
                const searchStr = `${p.nombre || ''} ${p.codigo || ''} ${p.sector_nombre || ''} ${p.profesional_1 || ''}`.toLowerCase();
                if (!searchStr.includes(term)) return false;

                return Object.keys(currentFilters).every(key => {
                    if (currentFilters[key].length === 0) return true;
                    // Multi-field check for professional
                    if (key === 'profesional') {
                        const profs = [p.profesional_1, p.profesional_2, p.profesional_3].filter(Boolean);
                        return currentFilters[key].some(v => profs.includes(v));
                    }
                    return currentFilters[key].includes(String(p[mapFilters[key]] || '').trim());
                });
            });

            renderProyectos(filteredData);
            if (typeof updateKPIs === 'function') updateKPIs(filteredData);
            if (typeof updateCount === 'function') updateCount(filteredData.length);
            populateFilters();
        }

        function renderSkeleton(container, rows = 5) {
            const visibilityClass = columnsVisible ? 'toggle-column-visible' : 'hidden';
            container.innerHTML = Array(rows).fill(0).map(() => `
                <tr class="animate-pulse bg-white">
                    <td class="toggle-column ${visibilityClass} px-6 py-8"><div class="h-3 bg-slate-100 rounded w-8 mx-auto"></div></td>
                    <td class="px-6 py-8">
                        <div class="h-5 bg-slate-100 rounded w-3/4 mb-3"></div>
                        <div class="h-3 bg-slate-50 rounded w-1/2"></div>
                    </td>
                    <td class="toggle-column ${visibilityClass} px-6 py-8"><div class="h-4 bg-slate-100 rounded w-full"></div></td>
                    <td class="toggle-column ${visibilityClass} px-6 py-8"><div class="h-4 bg-slate-100 rounded w-20 mx-auto"></div></td>
                    <td class="toggle-column ${visibilityClass} px-6 py-8"><div class="h-5 bg-slate-100 rounded w-24 ml-auto"></div></td>
                    <td class="px-6 py-8"><div class="h-8 bg-slate-50 rounded-full w-28 mx-auto"></div></td>
                    <td class="px-6 py-8"><div class="h-2 bg-slate-100 rounded-full w-full"></div></td>
                    <td class="px-6 py-8"><div class="h-10 bg-slate-50 rounded-xl w-32 mx-auto"></div></td>
                </tr>
            `).join('');
        }

        function renderProyectos(proyectosToRender) {
            const tableBody = document.getElementById('projectsTableBody');
            if (proyectosToRender.length === 0) {
                tableBody.innerHTML = `
                    <tr>
                        <td colspan="8" class="text-center py-20 bg-slate-50/20">
                            <i class="fas fa-ghost text-4xl text-slate-200 mb-4 block"></i>
                            <p class="font-extrabold text-slate-400 uppercase tracking-widest text-[11px]">Cero coincidencias encontradas</p>
                            <p class="text-sm text-gray-400 mt-2">Intenta ajustar los filtros de bÃºsqueda</p>
                        </td>
                    </tr>
                `;
                return;
            }

            const visibilityClass = columnsVisible ? 'toggle-column-visible' : 'hidden';

            tableBody.innerHTML = proyectosToRender.map((proyecto, i) => {
                let statusClass = utils.getStatusClass(proyecto.estado_nombre || '');
                let statusText = proyecto.estado_nombre || 'N/A';
                let cStyle = proyecto.estado_color ? `background-color: ${proyecto.estado_color}10; color: ${proyecto.estado_color}; border: 1px solid ${proyecto.estado_color}30;` : '';

                let progressClass = '';
                const progress = proyecto.avance_total_porcentaje ? parseFloat(proyecto.avance_total_porcentaje) : 0;
                const displayProgress = (progress > 1 ? progress : progress * 100).toFixed(0);

                if (displayProgress < 30) progressClass = 'bg-rose-500';
                else if (displayProgress < 70) progressClass = 'bg-amber-500';
                else progressClass = 'bg-emerald-500';

                return `
                    <tr class="stagger-item group hover:bg-slate-50/50 transition-colors duration-200" style="animation-delay: ${i * 0.02}s">
                        <td class="toggle-column ${visibilityClass} px-6 py-5 text-center" data-label="ID">
                            <span class="font-mono text-[10px] font-black text-slate-400">#${proyecto.id || ''}</span>
                        </td>
                        <td class="px-6 py-5" data-label="DescripciÃ³n">
                            <div class="max-w-md">
                                <h4 class="text-xs md:text-sm font-bold text-slate-900 group-hover:text-indigo-600 transition-colors truncate" title="${proyecto.nombre || ''}">${proyecto.nombre || 'Proyecto sin denominaciÃ³n'}</h4>
                                <div class="flex items-center gap-3 mt-1.5 overflow-hidden">
                                    <span class="shrink-0 text-[9px] font-black bg-slate-100 text-slate-500 px-1.5 py-0.5 rounded tracking-tighter">${proyecto.codigo || 'S/N'}</span>
                                    <span class="text-[10px] text-slate-400 font-bold truncate"><i class="fas fa-location-dot mr-1 opacity-40"></i> ${proyecto.sector_nombre || 'General Algarrobo'}</span>
                                </div>
                            </div>
                        </td>
                        <td class="toggle-column ${visibilityClass} px-6 py-5" data-label="Ãrea">
                            <p class="text-[11px] font-black text-slate-700 uppercase leading-none">${proyecto.area_nombre || '-'}</p>
                            <span class="text-[9px] font-bold text-slate-400 uppercase tracking-tight opacity-70">${proyecto.lineamiento_nombre || '-'}</span>
                        </td>
                        <td class="toggle-column ${visibilityClass} px-6 py-5 text-center" data-label="Fuente">
                            <span class="text-[10px] font-black text-indigo-400 uppercase tracking-widest">${proyecto.financiamiento_nombre || '-'}</span>
                        </td>
                        <td class="toggle-column ${visibilityClass} px-6 py-5 text-right font-mono text-sm font-semibold text-slate-900" data-label="Monto">
                            ${utils.formatCurrency(proyecto.monto)}
                        </td>
                        <td class="px-6 py-5 text-center" data-label="Estado">
                            <span class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-[10px] font-black uppercase tracking-wider" style="${cStyle}">
                                <span class="w-1.5 h-1.5 rounded-full" style="background:${proyecto.estado_color || '#ccc'}"></span>
                                ${statusText}
                            </span>
                        </td>
                        <td class="px-6 py-5" data-label="Progreso">
                            <div class="flex items-center gap-3">
                                <div class="grow h-2 bg-slate-100 rounded-full overflow-hidden shadow-inner">
                                    <div class="${progressClass} h-full rounded-full transition-all duration-1000" style="width: ${displayProgress}%"></div>
                                </div>
                                <span class="text-[10px] font-black text-slate-700 w-8 text-right">${displayProgress}%</span>
                            </div>
                        </td>
                        <td class="px-6 py-5" data-label="GestiÃ³n">
                            <div class="flex justify-center items-center gap-2">
                                <button onclick="viewProject(${proyecto.id})" class="w-8 h-8 md:w-9 md:h-9 bg-slate-50 text-slate-400 hover:bg-slate-900 hover:text-white rounded-xl transition-all shadow-sm tooltip" title="Ver detalles"><i class="fas fa-eye text-xs"></i></button>
                                <button onclick="editProject(${proyecto.id})" class="w-8 h-8 md:w-9 md:h-9 bg-slate-50 text-slate-400 hover:bg-indigo-600 hover:text-white rounded-xl transition-all shadow-sm tooltip" title="Editar ParÃ¡metros"><i class="fas fa-pen text-xs"></i></button>
                                <button onclick="deleteProject(${proyecto.id})" class="w-8 h-8 md:w-9 md:h-9 bg-slate-50 text-slate-400 hover:bg-rose-500 hover:text-white rounded-xl transition-all shadow-sm tooltip" title="Eliminar"><i class="fas fa-trash-alt text-xs"></i></button>
                            </div>
                        </td>
                    </tr>
                `;
            }).join('');
        }

        function updateKPIs(proyectosData) {
            document.getElementById('totalProjects').textContent = proyectosData.length;

            const executionCount = proyectosData.filter(p => p.estado_nombre === 'EjecuciÃ³n').length;
            document.getElementById('executionProjects').textContent = executionCount;
            const totalAmount = proyectosData.reduce((sum, p) => sum + (parseFloat(p.monto) || 0), 0);
            document.getElementById('totalAmount').textContent = utils.formatCurrency(totalAmount);
            const avgProgress = proyectosData.length > 0
                ? proyectosData.reduce((sum, p) => sum + (parseFloat(p.avance_total_porcentaje) || 0), 0) / proyectosData.length
                : 0;
            document.getElementById('averageProgress').textContent = (avgProgress > 1 ? avgProgress : avgProgress * 100).toFixed(1) + '%';
        }

        function toggleColumns() {
            const toggleElements = document.querySelectorAll('.toggle-column');
            const toggleBtn = document.getElementById('toggleColumnsBtn');
            columnsVisible = !columnsVisible;

            toggleElements.forEach(el => {
                el.classList.toggle('toggle-column-visible', columnsVisible);
                if (columnsVisible) {
                    el.classList.remove('hidden');
                } else {
                    el.classList.add('hidden');
                }
            });

            if (columnsVisible) {
                toggleBtn.innerHTML = '<i class="fas fa-compress-arrows-alt mr-2"></i>Vista Compacta';
            } else {
                toggleBtn.innerHTML = '<i class="fas fa-expand-arrows-alt mr-2"></i>Vista Expandida';
            }
        }

        function updateCount(count) {
            const countElement = document.getElementById('proyectoCount');
            if (countElement) {
                countElement.textContent = `${count} proyecto${count !== 1 ? 's' : ''} encontrados`;
            }
        }

        async function viewProject(id) {
            const proyecto = proyectos.find(p => p.id === id);
            if (!proyecto) {
                showToast('Proyecto no encontrado', 'error');
                return;
            }

            // Registrar actividad ver_proyecto (fire-and-forget)
            api.post('/control/registrar', {
                accion: 'ver_proyecto',
                modulo: 'proyectos',
                entidad_tipo: 'proyecto',
                entidad_id: id,
                entidad_nombre: proyecto.nombre || `Proyecto #${id}`,
                exitoso: true
            }).catch(() => { }); // silencioso â€” no interrumpe la UI

            let projectDocs = [];
            let proximosPasos = [];
            let ultimosCambios = [];

            try {
                const docResponse = await api.get(`/proyectos/${id}/documentos`);
                projectDocs = docResponse.documentos || [];
            } catch (e) { }

            try {
                const pxResponse = await api.get(`/proyectos/${id}/proximos_pasos`);
                if (Array.isArray(pxResponse)) proximosPasos = pxResponse;
                else if (pxResponse.proximos_pasos) proximosPasos = pxResponse.proximos_pasos;
            } catch (e) { }

            try {
                const actResponse = await api.get(`/control/actividad/proyecto/${id}`);
                if (actResponse && actResponse.actividad) {
                    ultimosCambios = actResponse.actividad.slice(0, 10);
                }
            } catch (e) { }

            const detailsContainer = document.getElementById('viewProjectDetails');
            detailsContainer.innerHTML = '';

            const formatDocProgress = (val) => {
                if (!val) return '<span class="text-sm font-semibold text-gray-400">-</span>';
                const num = parseFloat(val);
                if (isNaN(num)) return `<span class="text-sm font-semibold text-gray-900">${val}</span>`;
                const perc = num * 100;
                let colorClass = '';
                if (perc <= 20) colorClass = 'bg-red-50 text-red-700 border-red-200 shadow-sm';
                else if (perc <= 40) colorClass = 'bg-orange-50 text-orange-700 border-orange-200 shadow-sm';
                else if (perc <= 60) colorClass = 'bg-amber-50 text-amber-700 border-amber-200 shadow-sm';
                else if (perc <= 80) colorClass = 'bg-blue-50 text-blue-700 border-blue-200 shadow-sm';
                else colorClass = 'bg-emerald-50 text-emerald-700 border-emerald-200 shadow-sm';

                return `<span class="inline-flex items-center px-2.5 py-1 rounded-lg text-xs font-black border uppercase tracking-wider ${colorClass}">${perc.toFixed(0)}%</span>`;
            };

            let html = `
                <div class="space-y-6">
                    <!-- Basic Info Banner -->
                    <div class="bg-white rounded-2xl p-6 shadow-sm border border-gray-100 flex flex-col md:flex-row items-center gap-6">
                        <div class="flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-600 text-white shadow-lg text-2xl font-bold flex-shrink-0">
                            <i class="fas fa-project-diagram"></i>
                        </div>
                        <div class="flex-1 text-center md:text-left">
                            <h3 class="text-2xl font-bold text-gray-900 mb-2">${proyecto.nombre || 'Sin denominaciÃ³n'}</h3>
                            <div class="flex flex-wrap items-center justify-center md:justify-start gap-3">
                                <span class="inline-flex items-center px-3 py-1 rounded-lg text-xs font-black bg-indigo-50 text-indigo-700 tracking-wider">
                                    <i class="fas fa-hashtag mr-1.5 opacity-50"></i> ${proyecto.codigo || 'N/A'}
                                </span>
                                <span class="inline-flex items-center px-3 py-1 rounded-lg text-xs font-black bg-emerald-50 text-emerald-700 tracking-wider uppercase">
                                    <i class="fas fa-layer-group mr-1.5 opacity-50"></i> ${proyecto.area_nombre || 'Sin Ãrea'}
                                </span>
                                <span class="inline-flex items-center px-3 py-1 rounded-lg text-xs font-black bg-blue-50 text-blue-700 tracking-wider uppercase" style="${proyecto.estado_color ? `background-color: ${proyecto.estado_color}1a; color: ${proyecto.estado_color}; border: 1px solid ${proyecto.estado_color}33;` : ''}">
                                    <i class="fas fa-flag mr-1.5 opacity-50"></i> ${proyecto.estado_nombre || 'Sin Estado'}
                                </span>
                            </div>
                        </div>
                        <div class="text-center md:text-right w-full md:w-auto mt-4 md:mt-0 pt-4 md:pt-0 border-t md:border-t-0 border-slate-100">
                            <div class="text-[10px] font-black uppercase tracking-widest text-slate-400 mb-1">Monto InversiÃ³n</div>
                            <div class="text-2xl font-black text-indigo-600 font-mono tracking-tight">${utils.formatCurrency(proyecto.monto)}</div>
                        </div>
                    </div>

                    <!-- Main Grid -->
                    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
                        
                        <!-- Columna Izquierda -->
                        <div class="space-y-6">
                            
                            <!-- Info General -->
                            <div class="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden">
                                <div class="bg-slate-50 border-b border-slate-100 px-5 py-4 flex items-center gap-3">
                                    <div class="w-8 h-8 rounded-lg bg-indigo-100 text-indigo-600 flex items-center justify-center text-sm">
                                        <i class="fas fa-info-circle"></i>
                                    </div>
                                    <h4 class="font-bold text-slate-800 text-sm">InformaciÃ³n General</h4>
                                </div>
                                <div class="p-5 space-y-3">
                                    <div class="flex justify-between items-center py-2 border-b border-dashed border-slate-200">
                                        <span class="text-xs font-bold text-slate-500 uppercase tracking-wider">Estado del Proyecto:</span>
                                        <span class="text-xs font-black text-slate-800">${proyecto.estado_nombre || '-'}</span>
                                    </div>
                                    <div class="flex justify-between items-center py-2 border-b border-dashed border-slate-200">
                                        <span class="text-xs font-bold text-slate-500 uppercase tracking-wider">Etapa:</span>
                                        <span class="text-xs font-black text-slate-800">${proyecto.etapa_nombre || '-'}</span>
                                    </div>
                                    <div class="flex justify-between items-center py-2 border-b border-dashed border-slate-200">
                                        <span class="text-xs font-bold text-slate-500 uppercase tracking-wider">PostulaciÃ³n:</span>
                                        <span class="text-xs font-black text-slate-800">${proyecto.estado_postulacion_nombre || '-'}</span>
                                    </div>
                                    <div class="flex justify-between items-center py-2 border-b border-dashed border-slate-200">
                                        <span class="text-xs font-bold text-slate-500 uppercase tracking-wider">Avance FÃ­sico:</span>
                                        <div class="flex items-center gap-2">
                                            <div class="w-24 h-2 bg-slate-100 rounded-full overflow-hidden">
                                                <div class="h-full bg-indigo-500 rounded-full" style="width: ${parseFloat(proyecto.avance_total_porcentaje) > 1 ? parseFloat(proyecto.avance_total_porcentaje) : parseFloat(proyecto.avance_total_porcentaje || 0) * 100}%"></div>
                                            </div>
                                            <span class="text-xs font-black text-indigo-600">${proyecto.avance_total_porcentaje ? `${(parseFloat(proyecto.avance_total_porcentaje) > 1 ? parseFloat(proyecto.avance_total_porcentaje) : parseFloat(proyecto.avance_total_porcentaje) * 100).toFixed(0)}%` : '-'}</span>
                                        </div>
                                    </div>
                                    <div class="flex justify-between items-center py-2">
                                        <span class="text-xs font-bold text-slate-500 uppercase tracking-wider">Prioridad:</span>
                                        <span class="text-xs font-black ${proyecto.es_prioridad === 'SI' ? 'text-red-600 bg-red-50 px-2.5 py-1.5 rounded-lg' : 'text-slate-700 bg-slate-50 px-2.5 py-1.5 rounded-lg'}">
                                            ${proyecto.es_prioridad === 'SI' ? '<i class="fas fa-fire mr-1 text-red-500"></i> CrÃ­tico' : '<i class="fas fa-minus mr-1 opacity-50"></i> Normal'}
                                        </span>
                                    </div>
                                </div>
                            </div>
                            
                            <!-- DocumentaciÃ³n y TÃ©cnica -->
                            <div class="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden">
                                <div class="bg-slate-50 border-b border-slate-100 px-5 py-4 flex items-center gap-3">
                                    <div class="w-8 h-8 rounded-lg bg-emerald-100 text-emerald-600 flex items-center justify-center text-sm">
                                        <i class="fas fa-file-contract"></i>
                                    </div>
                                    <h4 class="font-bold text-slate-800 text-sm">Estado Documental y TÃ©cnico</h4>
                                </div>
                                <div class="p-5 space-y-3">
                                    <div class="flex justify-between items-center py-2 border-b border-dashed border-slate-200">
                                        <span class="text-xs font-bold text-slate-500 uppercase tracking-wider">Documentos:</span>
                                        ${formatDocProgress(proyecto.documentos)}
                                    </div>
                                    <div class="flex justify-between items-center py-2 border-b border-dashed border-slate-200">
                                        <span class="text-xs font-bold text-slate-500 uppercase tracking-wider">PlanimetrÃ­as:</span>
                                        ${formatDocProgress(proyecto.planimetrias)}
                                    </div>
                                    <div class="flex justify-between items-center py-2 border-b border-dashed border-slate-200">
                                        <span class="text-xs font-bold text-slate-500 uppercase tracking-wider">TopografÃ­a:</span>
                                        ${formatDocProgress(proyecto.topografia)}
                                    </div>
                                    <div class="flex justify-between items-center py-2 border-b border-dashed border-slate-200">
                                        <span class="text-xs font-bold text-slate-500 uppercase tracking-wider">IngenierÃ­a:</span>
                                        ${formatDocProgress(proyecto.ingenieria)}
                                    </div>
                                    <div class="flex justify-between items-center py-2 border-b border-dashed border-slate-200">
                                        <span class="text-xs font-bold text-slate-500 uppercase tracking-wider">Perfil T.E.:</span>
                                        ${formatDocProgress(proyecto.perfil_tecnico_economico)}
                                    </div>
                                    <div class="flex justify-between items-center py-2 border-b border-dashed border-slate-200">
                                        <span class="text-xs font-bold text-slate-500 uppercase tracking-wider">AprobaciÃ³n DOM:</span>
                                        ${formatDocProgress(proyecto.aprobacion_dom)}
                                    </div>
                                    <div class="flex justify-between items-center py-2">
                                        <span class="text-xs font-bold text-slate-500 uppercase tracking-wider">AprobaciÃ³n SERVIU:</span>
                                        ${formatDocProgress(proyecto.aprobacion_serviu)}
                                    </div>
                                </div>
                            </div>
                            
                            <!-- Financiamiento y Territorio Integrado -->
                            <div class="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden">
                                <div class="bg-slate-50 border-b border-slate-100 px-5 py-4 flex items-center gap-3">
                                    <div class="w-8 h-8 rounded-lg bg-amber-100 text-amber-600 flex items-center justify-center text-sm">
                                        <i class="fas fa-coins"></i>
                                    </div>
                                    <h4 class="font-bold text-slate-800 text-sm">Finanzas y Territorio</h4>
                                </div>
                                <div class="p-5 grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-4">
                                    <div class="flex flex-col">
                                        <span class="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1">Fuente InversiÃ³n</span>
                                        <span class="text-sm font-black text-slate-800">${proyecto.financiamiento_nombre || '-'}</span>
                                    </div>
                                    <div class="flex flex-col">
                                        <span class="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1">Aporte Municipal</span>
                                        <span class="text-sm font-black text-slate-800">${proyecto.financiamiento_municipal || '-'}</span>
                                    </div>
                                    <div class="flex flex-col">
                                        <span class="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1">AsignaciÃ³n Territorial</span>
                                        <span class="text-sm font-black text-slate-800"><i class="fas fa-map-marker-alt text-slate-400 mr-1.5"></i> ${proyecto.sector_nombre || '-'}</span>
                                    </div>
                                    <div class="col-span-1 md:col-span-2 flex flex-col pt-3 border-t border-dashed border-slate-100 mt-2">
                                        <span class="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1">Lineamiento Base</span>
                                        <span class="text-sm font-semibold text-slate-800 italic">${proyecto.lineamiento_nombre || '-'}</span>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- Columna Derecha -->
                        <div class="space-y-6">
                            
                            <!-- Observaciones Generales -->
                            <div class="bg-gradient-to-br from-amber-50 to-orange-50 rounded-2xl shadow-sm border border-amber-200 overflow-hidden">
                                <div class="px-5 py-4 flex items-center gap-3 border-b border-amber-200/50">
                                    <div class="w-8 h-8 rounded-lg bg-orange-100 text-orange-600 flex items-center justify-center text-sm">
                                        <i class="fas fa-comment-alt"></i>
                                    </div>
                                    <h4 class="font-bold text-slate-800 text-sm">Notas y Observaciones</h4>
                                </div>
                                <div class="p-5">
                                    <p class="text-sm text-slate-700 italic leading-relaxed">
                                        ${proyecto.observaciones ? proyecto.observaciones : '<span class="text-slate-400 font-medium">No se han registrado observaciones generales ni comentarios extendidos para este proyecto.</span>'}
                                    </p>
                                </div>
                            </div>
                            
                            <!-- PrÃ³ximos Pasos -->
                            <div class="bg-white rounded-2xl shadow-sm border border-indigo-100 overflow-hidden">
                                <div class="bg-indigo-50 border-b border-indigo-100 px-5 py-4 flex items-center gap-3">
                                    <div class="w-8 h-8 rounded-lg bg-indigo-600 text-white flex items-center justify-center text-sm shadow-md shadow-indigo-200">
                                        <i class="fas fa-forward"></i>
                                    </div>
                                    <h4 class="font-bold text-indigo-900 text-sm">Responsabilidad PrÃ³ximos Pasos</h4>
                                </div>
                                <div class="p-5">
                                    ${proximosPasos.length > 0 ? `
                                        <div class="space-y-4">
                                            ${proximosPasos.map(step => {
                let estadoColor = 'bg-slate-100 text-slate-700';
                switch (step.estado) {
                    case 'PENDIENTE': estadoColor = 'bg-amber-100 text-amber-700 border border-amber-200'; break;
                    case 'EN_PROCESO': estadoColor = 'bg-blue-100 text-blue-700 border border-blue-200'; break;
                    case 'COMPLETADO': estadoColor = 'bg-emerald-100 text-emerald-700 border border-emerald-200'; break;
                    case 'VENCIDO': estadoColor = 'bg-rose-100 text-rose-700 border border-rose-200'; break;
                }
                return `
                                                    <div class="flex gap-4 items-start pb-4 border-b border-dashed border-slate-100 last:border-0 last:pb-0">
                                                        <div class="w-1.5 h-1.5 rounded-full mt-2 bg-indigo-400 flex-shrink-0"></div>
                                                        <div class="flex-1 min-w-0">
                                                            <div class="flex items-start justify-between gap-2 mb-1">
                                                                <p class="text-sm font-bold text-slate-800 leading-tight">${step.comentario}</p>
                                                                <span class="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-black tracking-widest uppercase ${estadoColor}">${step.estado}</span>
                                                            </div>
                                                            <div class="flex items-center gap-3 text-[10px] font-bold text-slate-500 uppercase tracking-wider mt-2">
                                                                <span class="${new Date(step.fecha_plazo) < new Date() && step.estado !== 'COMPLETADO' ? 'text-rose-600' : ''}">
                                                                    <i class="far fa-calendar-alt mr-1"></i> PLAZO: ${formatDisplayDate(step.fecha_plazo).split(' ')[0]}
                                                                </span>
                                                                <span><i class="fas fa-user-circle mr-1"></i> ${step.responsable || 'Secplan'}</span>
                                                            </div>
                                                        </div>
                                                    </div>
                                                `;
            }).join('')}
                                        </div>
                                    ` : `
                                        <div class="text-center py-6">
                                            <i class="fas fa-calendar-check text-4xl text-slate-200 mb-3 block"></i>
                                            <p class="text-xs font-bold text-slate-500 uppercase tracking-widest">Sin pasos pendientes a la vista</p>
                                        </div>
                                    `}
                                </div>
                            </div>
                            
                            <!-- Equipo Responsable -->
                            <div class="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden">
                                <div class="bg-slate-50 border-b border-slate-100 px-5 py-4 flex items-center gap-3">
                                    <div class="w-8 h-8 rounded-lg bg-teal-100 text-teal-600 flex items-center justify-center text-sm">
                                        <i class="fas fa-users-cog"></i>
                                    </div>
                                    <h4 class="font-bold text-slate-800 text-sm">Equipo Consolidado</h4>
                                </div>
                                <div class="p-5">
                                    <div class="flex flex-wrap gap-2 mb-4">
                                        ${[proyecto.profesional_1, proyecto.profesional_2, proyecto.profesional_3, proyecto.profesional_4, proyecto.profesional_5].filter(Boolean).map(p => `
                                            <span class="inline-flex items-center px-3 py-1.5 bg-slate-100 text-slate-700 text-xs font-bold rounded-lg border border-slate-200">
                                                <i class="fas fa-user opacity-30 mr-2"></i> ${p}
                                            </span>
                                        `).join('')}
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            `;

            const hitos = proyecto.hitos_lista || [];
            if (hitos.length > 0) {
                html += `
                <div class="mt-8">
                <div class="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
                    <div class="bg-gradient-to-r from-blue-500 to-cyan-500 p-5">
                        <h3 class="text-xl font-bold text-white flex items-center gap-3">
                            <div class="bg-white bg-opacity-20 p-2 rounded-lg">
                                <i class="fas fa-flag-checkered"></i>
                            </div>
                            Hitos del Proyecto
                            <span class="ml-auto bg-white bg-opacity-20 px-3 py-1 rounded-full text-sm font-medium">${hitos.length} hito${hitos.length !== 1 ? 's' : ''}</span>
                        </h3>
                    </div>
                    <div class="p-6 space-y-4">
                        ${hitos.map((h, index) => `
                                        <div class="bg-gradient-to-r from-blue-50 to-cyan-50 rounded-xl p-5 border border-blue-100 hover:shadow-md transition-all">
                                            <div class="flex items-start gap-4">
                                                <div class="flex-shrink-0">
                                                    <div class="w-12 h-12 rounded-full bg-blue-500 text-white flex items-center justify-center font-bold text-lg">
                                                        ${index + 1}
                                                    </div>
                                                </div>
                                                <div class="flex-1 space-y-2">
                                                    <div class="flex items-center gap-3 flex-wrap">
                                                        <span class="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-blue-600 text-white">
                                                            <i class="fas fa-bookmark mr-1.5"></i>
                                                            ${h.tipo_hito || 'Sin tipo'}
                                                        </span>
                                                        <span class="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-white text-gray-700 border border-gray-300">
                                                            <i class="fas fa-calendar mr-1.5"></i>
                                                            ${formatDisplayDate(h.fecha)}
                                                        </span>
                                                    </div>
                                                    ${h.observacion ? `
                                                        <div class="bg-white rounded-lg p-3 mt-2">
                                                            <p class="text-sm text-gray-700 leading-relaxed">${h.observacion}</p>
                                                        </div>
                                                    ` : '<p class="text-sm text-gray-500 italic">Sin observaciÃ³n</p>'}
                                                    ${(h.nombre_creador || h.creado_por) ? `
                                                        <div class="text-xs text-gray-500 mt-2 flex items-center gap-1">
                                                            <i class="fas fa-user"></i>
                                                            Creado por: <span class="font-medium">${h.nombre_creador || 'Usuario #' + h.creado_por}</span>
                                                        </div>
                                                    ` : ''}
                                                </div>
                                            </div>
                                        </div>
                                    `).join('')}
                    </div>
                </div>
                </div >
                `;
            }

            const observaciones = proyecto.observaciones_lista || [];
            if (observaciones.length > 0) {
                html += `
                <div class="mt-6">
                    <div class="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
                        <div class="bg-gradient-to-r from-orange-500 to-amber-500 p-5">
                            <h3 class="text-xl font-bold text-white flex items-center gap-3">
                                <div class="bg-white bg-opacity-20 p-2 rounded-lg">
                                    <i class="fas fa-comments"></i>
                                </div>
                                Observaciones del Proyecto
                                <span class="ml-auto bg-white bg-opacity-20 px-3 py-1 rounded-full text-sm font-medium">${observaciones.length} observaciÃ³n${observaciones.length !== 1 ? 'es' : ''}</span>
                            </h3>
                        </div>
                        <div class="p-6 space-y-4">
                            ${observaciones.map((o, index) => `
                                        <div class="bg-gradient-to-r from-orange-50 to-amber-50 rounded-xl p-5 border border-orange-100 hover:shadow-md transition-all">
                                            <div class="flex items-start gap-4">
                                                <div class="flex-shrink-0">
                                                    <div class="w-12 h-12 rounded-full bg-orange-500 text-white flex items-center justify-center font-bold text-lg">
                                                        ${index + 1}
                                                    </div>
                                                </div>
                                                <div class="flex-1">
                                                    <div class="flex items-center gap-3 mb-3">
                                                        <span class="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-white text-gray-700 border border-gray-300">
                                                            <i class="fas fa-calendar mr-1.5"></i>
                                                            ${formatDisplayDate(o.fecha)}
                                                        </span>
                                                        ${(o.nombre_creador || o.creado_por) ? `
                                                            <span class="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-orange-600 text-white">
                                                                <i class="fas fa-user mr-1.5"></i>
                                                                ${o.nombre_creador || 'Usuario #' + o.creado_por}
                                                            </span>
                                                        ` : ''}
                                                    </div>
                                                    <div class="bg-white rounded-lg p-4">
                                                        <p class="text-sm text-gray-800 leading-relaxed">${o.observacion || 'Sin observaciÃ³n'}</p>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    `).join('')}
                        </div>
                    </div>
                </div >
                `;
            }

            html += `
                <div class="mt-8">
                    <div class="bg-gradient-to-r from-gray-700 to-gray-900 rounded-2xl shadow-lg p-6 text-white">
                        <h3 class="text-lg font-bold mb-4 flex items-center gap-2">
                            <i class="fas fa-shield-alt"></i>
                            AuditorÃ­a del Sistema
                        </h3>
                        <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mt-6">
                            <div class="bg-white bg-opacity-10 rounded-2xl p-4 backdrop-blur shadow-inner">
                                <div class="text-[10px] uppercase font-black tracking-widest text-slate-400 mb-1">Creado por</div>
                                <div class="font-bold text-sm truncate" title="${proyecto.user_nombre}">${proyecto.user_nombre || 'Desconocido'}</div>
                            </div>
                            <div class="bg-white bg-opacity-10 rounded-2xl p-4 backdrop-blur shadow-inner">
                                <div class="text-[10px] uppercase font-black tracking-widest text-slate-400 mb-1">Actualizado por</div>
                                <div class="font-bold text-sm truncate" title="${proyecto.actualizado_por_nombre}">${proyecto.actualizado_por_nombre || 'Desconocido'}</div>
                            </div>
                            <div class="bg-white bg-opacity-10 rounded-2xl p-4 backdrop-blur shadow-inner">
                                <div class="text-[10px] uppercase font-black tracking-widest text-slate-400 mb-1">Ãšltima modificaciÃ³n</div>
                                <div class="font-bold text-sm">${formatDisplayDate(proyecto.fecha_actualizacion).split(' ')[0] || 'Desconocido'}</div>
                            </div>
                            <div class="bg-white bg-opacity-10 rounded-2xl p-4 backdrop-blur shadow-inner">
                                <div class="text-[10px] uppercase font-black tracking-widest text-slate-400 mb-1">AuditorÃ­a Total</div>
                                <div class="font-bold text-sm">${ultimosCambios.length} cambios recientes</div>
                            </div>
                        </div>

                        ${ultimosCambios.length > 0 ? `
                        <div class="mt-6">
                            <h4 class="text-sm font-bold text-gray-300 mb-3 uppercase tracking-wider">Ãšltimos 10 Cambios</h4>
                            <div class="space-y-3">
                                ${ultimosCambios.map(c => `
                                    <div class="bg-white bg-opacity-5 rounded-lg p-4 flex flex-col md:flex-row gap-4 justify-between items-start md:items-center">
                                        <div>
                                            <div class="flex items-center gap-2 mb-1">
                                                <span class="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-black tracking-widest uppercase bg-blue-500 bg-opacity-20 text-blue-300 border border-blue-500 border-opacity-30">
                                                    ${c.accion}
                                                </span>
                                                <span class="text-xs font-medium text-gray-400">
                                                    <i class="far fa-calendar-alt mr-1"></i> ${formatDisplayDate(c.fecha)}
                                                </span>
                                            </div>
                                            <p class="text-sm text-gray-200">${c.detalle || 'Sin detalles'}</p>
                                        </div>
                                        <div class="flex items-center gap-2 text-xs text-gray-400 bg-black bg-opacity-20 px-3 py-1.5 rounded-full">
                                            <i class="fas fa-user-circle"></i>
                                            ${c.nombre_usuario || 'Sistema'}
                                        </div>
                                    </div>
                                `).join('')}
                            </div>
                        </div>
                        ` : ''}

                    </div>
                </div >
                `;

            detailsContainer.innerHTML = html;

            const btnDownload = document.getElementById('btnDownloadReport');
            if (btnDownload) {
                btnDownload.onclick = () => downloadProjectPDF(id);
            }

            document.getElementById('viewProjectModal').classList.add('active');
        }

        function editProject(id) {
            const proyecto = proyectos.find(p => p.id === id);
            if (proyecto) openModal(proyecto);
        }

        async function deleteProject(id) {
            if (!confirm('Â¿EstÃ¡ seguro de que desea eliminar este proyecto? Esta acciÃ³n no se puede deshacer.')) return;

            try {

                if (typeof showLoading === 'function') showLoading(true, 'Eliminando...');

                await api.delete(`/proyectos/${id}`);

                showToast('Proyecto eliminado exitosamente', 'success');
                loadProjects();
            } catch (error) {
                console.error('Error:', error);
                showToast(error.message || 'Error al eliminar el proyecto', 'error');
            } finally {
                if (typeof showLoading === 'function') showLoading(false);
            }
        }

        function exportData() {
            showToast('FunciÃ³n de exportaciÃ³n en desarrollo', 'warning');
        }


        function showAddProjectModal() {
            openModal();
        }

        function openModal(proyecto = null) {

            if (catalogData.areas.length === 0) {
                populateFormSelects();
            }

            const modal = document.getElementById('proyectoModal');
            const form = document.getElementById('proyectoForm');
            const titleText = document.getElementById('modalTitleText');
            const modalIcon = document.getElementById('modalIcon');
            const modalSubtitle = document.getElementById('modalSubtitle');
            const submitText = document.getElementById('submitText');

            if (proyecto) {

                titleText.textContent = 'Editar Proyecto';
                modalIcon.className = 'fas fa-edit';
                modalSubtitle.textContent = 'Modifique los campos necesarios para actualizar el proyecto';
                submitText.textContent = 'Actualizar';
                editingId = proyecto.id;

                form.reset();

                // Mapear campos del objeto proyecto a los nombres del formulario
                // El backend devuelve area_id, estado_proyecto_id, etc. que coinciden con los names del form
                const fieldMapping = {
                    // Los campos _nombre son de solo lectura, ignorar
                    'area_nombre': null,
                    'estado_nombre': null,
                    'etapa_nombre': null,
                    'estado_postulacion_nombre': null,
                    'financiamiento_nombre': null,
                    'lineamiento_nombre': null,
                    'sector_nombre': null,
                    'estado_color': null
                };

                Object.keys(proyecto).forEach(key => {
                    // Saltar campos marcados como null en el mapping (campos de solo lectura)
                    if (key in fieldMapping && fieldMapping[key] === null) return;
                    const fieldName = fieldMapping[key] || key;
                    const input = form.elements[fieldName];
                    if (input) {
                        if (input.type === 'checkbox') {
                            input.checked = (proyecto[key] === 'SI' || proyecto[key] === true);
                        } else if (input.type === 'date') {
                            input.value = formatDateForInput(proyecto[key]);
                        } else if (key === 'avance_total_porcentaje') {
                            // Normalizar decimal (DB 0-1) a porcentaje (UI 0-100)
                            const val = parseFloat(proyecto[key]);
                            if (!isNaN(val)) {
                                input.value = (val <= 1.0 && val > 0) ? (val * 100).toFixed(2) : val;
                                if (val === 1.0) input.value = 100;
                            } else {
                                input.value = '';
                            }
                        } else {
                            input.value = proyecto[key] || '';
                        }
                    }
                });

                // Mostrar panel de enlaces rÃ¡pidos y cargar datos asÃ­ncronos
                const qab = document.getElementById('quickActionsBar');
                if (qab) {
                    qab.classList.remove('hidden');
                    qab.classList.add('flex');
                }

                const extraBlocks = ['proximosPasosContainer', 'hitosContainer', 'observacionesContainer', 'documentosContainer'];
                extraBlocks.forEach(id => {
                    const el = document.getElementById(id);
                    if (el) el.classList.remove('hidden');
                });

                // Disparar las llamadas asÃ­ncronas para inyectar la informaciÃ³n en los paneles
                if (typeof loadProximosPasos === 'function') loadProximosPasos(proyecto.id);
                if (typeof loadHitos_edit === 'function') loadHitos_edit(proyecto.id);
                if (typeof loadObservaciones_edit === 'function') loadObservaciones_edit(proyecto.id);
                if (typeof loadDocumentos_edit === 'function') loadDocumentos_edit(proyecto.id);

            } else {

                titleText.textContent = 'Nuevo Proyecto';
                modalIcon.className = 'fas fa-folder-plus';
                modalSubtitle.textContent = 'Complete los campos para registrar un nuevo proyecto';
                submitText.textContent = 'Guardar';
                editingId = null;
                form.reset();

                // Ocultar sub-paneles
                const qab = document.getElementById('quickActionsBar');
                if (qab) {
                    qab.classList.add('hidden');
                    qab.classList.remove('flex');
                }

                const extraBlocks = ['proximosPasosContainer', 'hitosContainer', 'observacionesContainer', 'documentosContainer'];
                extraBlocks.forEach(id => {
                    const el = document.getElementById(id);
                    if (el) el.classList.add('hidden');
                });

            }
            modal.classList.add('active');
        }

        function closeModal() {
            document.getElementById('proyectoModal').classList.remove('active');
            document.getElementById('proyectoForm').reset();
            editingId = null;
        }

        function closeViewModal() {
            document.getElementById('viewProjectModal').classList.remove('active');
        }

        async function handleSubmit(e) {
            e.preventDefault();
            const form = e.target;
            const data = utils.serializeForm(form);

            // Checkbox: financiamiento_municipal es VARCHAR(50) en DB
            data.financiamiento_municipal = document.getElementById('financiamiento_municipal').checked ? 'SI' : 'NO';

            // FK IDs: parsear como enteros, eliminar si vacÃ­os
            const fkFields = ['area_id', 'estado_proyecto_id', 'etapa_proyecto_id', 'estado_postulacion_id', 'financiamiento_id', 'lineamiento_estrategico_id', 'sector_id'];
            fkFields.forEach(f => {
                if (data[f]) data[f] = parseInt(data[f], 10);
                else delete data[f];
            });

            // Campos numÃ©ricos: parsear o eliminar si vacÃ­os
            if (data.monto) data.monto = parseFloat(data.monto); else delete data.monto;
            if (data.avance_total_porcentaje) {
                // Convertir porcentaje (UI 0-100) a decimal (DB 0-1)
                const val = parseFloat(data.avance_total_porcentaje);
                data.avance_total_porcentaje = val / 100;
            } else {
                delete data.avance_total_porcentaje;
            }
            if (data.n_registro) data.n_registro = parseInt(data.n_registro, 10); else delete data.n_registro;
            if (data.anno_elaboracion) data.anno_elaboracion = parseInt(data.anno_elaboracion, 10); else delete data.anno_elaboracion;
            if (data.anno_ejecucion) data.anno_ejecucion = parseInt(data.anno_ejecucion, 10); else delete data.anno_ejecucion;
            if (data.latitud) data.latitud = parseFloat(data.latitud); else delete data.latitud;
            if (data.longitud) data.longitud = parseFloat(data.longitud); else delete data.longitud;

            // Eliminar campos que NO existen en la tabla proyectos
            delete data.codigo;
            delete data.es_prioridad;

            // Eliminar strings vacÃ­os para campos opcionales
            Object.keys(data).forEach(k => {
                if (data[k] === '') delete data[k];
            });

            console.log('Sending payload (schema-aligned):', data);

            const submitBtn = document.getElementById('submitBtn');
            const submitText = document.getElementById('submitText');
            const originalText = submitText.innerHTML;

            try {
                submitBtn.disabled = true;
                submitText.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i> Procesando...';

                if (editingId) {
                    await api.put(`/proyectos/${editingId}`, data);
                } else {
                    await api.post('/proyectos', data);
                }

                showToast(editingId ? 'Proyecto actualizado' : 'Proyecto creado exitosamente');
                closeModal();
                loadProjects();
            } catch (error) {
                console.error('Submit Error:', error);
                showToast(error.message || 'Error al guardar el proyecto', 'error');
            } finally {
                submitBtn.disabled = false;
                submitText.innerHTML = originalText;
            }
        }

        window.onclick = function (event) {
            const editModal = document.getElementById('proyectoModal');
            const viewModal = document.getElementById('viewProjectModal');
            if (event.target === editModal) closeModal();
            if (event.target === viewModal) closeViewModal();
        }

        document.addEventListener('keydown', function (event) {
            if (event.key === 'Escape') { closeModal(); closeViewModal(); }
        });

        function getFileIcon(ext) {
            if (!ext) return 'file';
            const e = ext.toLowerCase().replace('.', '');
            if (['pdf'].includes(e)) return 'pdf';
            if (['doc', 'docx'].includes(e)) return 'word';
            if (['xls', 'xlsx'].includes(e)) return 'excel';
            if (['jpg', 'jpeg', 'png', 'gif'].includes(e)) return 'image';
            if (['zip', 'rar'].includes(e)) return 'archive';
            return 'file';
        }

        async function handleQuickUpload(event, projectId) {
            const file = event.target.files[0];
            if (!file) return;

            const formData = new FormData();
            formData.append('file', file);
            formData.append('tipo_documento', 'Documento General');
            formData.append('descripcion', 'Subido desde visor de proyecto');

            const label = event.target.previousElementSibling;
            const originalText = label.innerHTML;
            label.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
            label.classList.add('cursor-not-allowed', 'opacity-50');

            try {
                // Use api wrapper for automatic auth and error handling
                await api.post(`/proyectos/${projectId}/documentos/upload`, formData);

                showToast('Documento subido correctamente');
                // Refresh view
                viewProject(projectId);
            } catch (error) {
                console.error(error);
                showToast(error.message || 'Error al subir archivo', 'error');
            } finally {
                label.innerHTML = originalText;
                label.classList.remove('cursor-not-allowed', 'opacity-50');
                event.target.value = '';
            }
        }

        // PDF Viewer Modal Functions
        // PDF Viewer Modal Functions
        function openDocViewer(docId, docName) {
            const url = `${API_CONFIG.BASE_URL.replace(/\/$/, '')}/documentos/${docId}/view?token=${API_CONFIG.token}`;
            window.open(url, '_blank');
        }

        function showAddProximoPasoForm() {
            document.getElementById('addProximoPasoForm').classList.remove('hidden');
        }

        function hideAddProximoPasoForm() {
            document.getElementById('addProximoPasoForm').classList.add('hidden');
            document.getElementById('addProximoPasoForm').reset();
            document.getElementById('pp_prioridad').value = 'MEDIA';
        }

        async function loadProximosPasos(pid) {
            const listContainer = document.getElementById('proximosPasosList');
            if (!listContainer) return;

            listContainer.innerHTML = '<div class="text-center py-4 text-gray-400 text-sm italic"><i class="fas fa-spinner fa-spin mr-2"></i> Cargando...</div>';

            try {
                const res = await api.get(`/proyectos/${pid}/proximos_pasos`);
                const pasos = res.proximos_pasos || [];

                if (pasos.length === 0) {
                    listContainer.innerHTML = '<div class="text-center py-4 bg-gray-50 rounded-lg text-gray-400 text-sm font-medium border border-gray-100">No hay prÃ³ximos pasos registrados.</div>';
                    return;
                }

                const htmlContent = pasos.map(p => {
                    const isCompleted = p.estado === 'COMPLETADO';
                    const pColor = p.prioridad === 'ALTA' ? 'text-rose-600 bg-rose-50 border-rose-200' : (p.prioridad === 'MEDIA' ? 'text-amber-600 bg-amber-50 border-amber-200' : 'text-emerald-600 bg-emerald-50 border-emerald-200');
                    const plazoDate = new Date(p.fecha_plazo + 'T12:00:00');

                    return `
                        <div class="flex items-center justify-between p-3 rounded-lg border border-gray-200 ${isCompleted ? 'bg-gray-100 opacity-60' : 'bg-gray-50/50'} hover:bg-gray-50 hover:border-indigo-200 transition group relative">
                            <div class="flex-1 min-w-0 pr-4">
                                <div class="flex items-center gap-2 mb-1">
                                    <span class="inline-flex items-center px-2.5 py-0.5 rounded text-[10px] font-bold border ${pColor} uppercase">${p.prioridad}</span>
                                    <span class="text-sm font-bold ${isCompleted ? 'text-gray-500 line-through' : 'text-gray-800'} truncate">${p.comentario}</span>
                                    ${isCompleted ? '<span class="text-[10px] bg-emerald-100 text-emerald-700 px-1.5 py-0.5 rounded font-bold">Hecho</span>' : ''}
                                </div>
                                <div class="flex items-center gap-3 text-xs text-gray-500">
                                    <span><i class="far fa-calendar mr-1"></i> ${plazoDate.toLocaleDateString('es-CL')}</span>
                                    ${p.responsable ? `<span><i class="far fa-user mr-1"></i> ${p.responsable}</span>` : '<span><i class="far fa-user opacity-50 mr-1"></i> Sin Asignar</span>'}
                                </div>
                            </div>
                            <div class="flex items-center gap-1 opacity-100 group-hover:opacity-100 transition-opacity">
                                <button type="button" onclick="toggleProximoPasoStatus(${p.id}, '${p.estado}')" class="p-1.5 rounded-md ${isCompleted ? 'text-amber-500 hover:bg-amber-100' : 'text-emerald-500 hover:bg-emerald-100'} transition-colors" title="${isCompleted ? 'Marcar Pendiente' : 'Marcar Completado'}">
                                    <i class="fas ${isCompleted ? 'fa-undo' : 'fa-check'}"></i>
                                </button>
                                <button type="button" onclick="deleteProximoPaso(${p.id})" class="p-1.5 rounded-md text-rose-500 hover:bg-rose-100 transition-colors" title="Eliminar">
                                    <i class="fas fa-trash-alt"></i>
                                </button>
                            </div>
                        </div>
                    `;
                }).join('');
                listContainer.innerHTML = htmlContent;
            } catch (error) {
                console.error(error);
                listContainer.innerHTML = '<div class="text-center py-4 bg-rose-50 rounded-lg text-rose-600 text-sm font-medium border border-rose-100">Error al cargar listado.</div>';
            }
        }

        async function saveProximoPaso(event) {
            event.preventDefault();
            if (!editingId) return;

            const btn = document.getElementById('pp_submitBtn');
            const originalText = btn.innerHTML;
            btn.disabled = true;
            btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';

            try {
                const payload = {
                    comentario: document.getElementById('pp_comentario').value,
                    fecha_plazo: document.getElementById('pp_fecha_plazo').value,
                    responsable: document.getElementById('pp_responsable').value || null,
                    prioridad: document.getElementById('pp_prioridad').value
                };

                await api.post(`/proyectos/${editingId}/proximos_pasos`, payload);
                showToast('PrÃ³ximo paso agregado correctamente', 'success');
                hideAddProximoPasoForm();
                loadProximosPasos(editingId);
            } catch (error) {
                console.error(error);
                showToast(error.message || 'Error al guardar el paso', 'error');
            } finally {
                btn.disabled = false;
                btn.innerHTML = originalText;
            }
        }

        async function toggleProximoPasoStatus(id, estadoActual) {
            if (!editingId) return;
            try {
                const nuevoEstado = estadoActual === 'COMPLETADO' ? 'PENDIENTE' : 'COMPLETADO';
                await api.put(`/proyectos/${editingId}/proximos_pasos/${id}`, { estado: nuevoEstado });
                loadProximosPasos(editingId);
            } catch (error) {
                console.error(error);
                // Si la ruta incluyente no funciona, intentamos el fallback genÃ©rico
                try {
                    const nuevoEstado = estadoActual === 'COMPLETADO' ? 'PENDIENTE' : 'COMPLETADO';
                    await api.put(`/proximos_pasos/${id}`, { estado: nuevoEstado });
                    loadProximosPasos(editingId);
                } catch (e) {
                    showToast('Error al actualizar estado', 'error');
                }
            }
        }

        async function deleteProximoPaso(id) {
            if (!editingId || !confirm('Â¿Eliminar este prÃ³ximo paso?')) return;
            try {
                await api.delete(`/proyectos/${editingId}/proximos_pasos/${id}`);
                loadProximosPasos(editingId);
            } catch (error) {
                console.error(error);
                try {
                    await api.delete(`/proximos_pasos/${id}`);
                    loadProximosPasos(editingId);
                } catch (e) {
                    showToast('Error al eliminar registro', 'error');
                }
            }
        }

        // ==========================================
        // FUNCIONES HITOS (Modal EdiciÃ³n)
        // ==========================================
        let categoriasHitoCache = null;

        async function fetchCategoriasHito() {
            if (categoriasHitoCache) return categoriasHitoCache;
            try {
                const data = await api.get('/hitoscalendario');
                categoriasHitoCache = data.filter(c => c.is_hito === true || c.is_hito === 'true' || c.is_hito === 1).sort((a, b) => a.nombre.localeCompare(b.nombre));

                const select = document.getElementById('h_categoria');
                if (select) {
                    select.innerHTML = '<option value="" disabled selected>Selecciona una categorÃ­a...</option>';
                    categoriasHitoCache.forEach(cat => {
                        const option = document.createElement('option');
                        option.value = cat.id; option.textContent = cat.nombre;
                        select.appendChild(option);
                    });
                }
                return categoriasHitoCache;
            } catch (e) { console.error('Categorias Error:', e); return []; }
        }

        function showAddHitoForm() {
            document.getElementById('addHitoForm').classList.remove('hidden');
            document.getElementById('h_fecha').value = new Date().toISOString().split('T')[0];
            fetchCategoriasHito(); // Asegurar categories existan
        }

        function hideAddHitoForm() {
            document.getElementById('addHitoForm').classList.add('hidden');
            document.getElementById('addHitoForm').reset();
        }

        async function loadHitos_edit(pid) {
            const list = document.getElementById('hitosList');
            if (!list) return;
            list.innerHTML = '<div class="text-center py-2 text-gray-400 text-sm italic"><i class="fas fa-spinner fa-spin mr-2"></i> Cargando hitos...</div>';

            try {
                const hitos = await api.get(`/proyectos/${pid}/hitos`);

                if (!hitos || hitos.length === 0) {
                    list.innerHTML = '<div class="text-center py-4 bg-gray-50 rounded-lg text-gray-400 text-sm font-medium border border-gray-100">No hay hitos en el proyecto.</div>';
                    return;
                }

                const htmlContent = hitos.map(h => {
                    const dateStr = h.fecha ? h.fecha.split('T')[0] : 'Sin fecha';
                    const catNombre = h.categoria_nombre || 'Hito';
                    return `
                    <div class="flex flex-col p-3 rounded-lg border border-gray-200 bg-gray-50/50 hover:bg-gray-50 transition">
                        <div class="flex items-center justify-between mb-1">
                            <span class="text-sm font-bold text-gray-800"><i class="fas fa-flag text-emerald-500 mr-2 text-xs"></i>${catNombre}</span>
                            <span class="text-xs font-mono text-gray-500">${dateStr}</span>
                        </div>
                        ${h.observacion ? `<span class="text-xs text-gray-600 pl-5">${h.observacion}</span>` : ''}
                    </div>`;
                }).join('');
                list.innerHTML = htmlContent;
            } catch (e) {
                console.error(e);
                list.innerHTML = '<div class="text-center py-2 text-rose-500 text-xs text-medium">Error al cargar hitos</div>';
            }
        }

        async function saveHito_edit(e) {
            e.preventDefault();
            if (!editingId) return;

            const btn = document.getElementById('h_submitBtn');
            const originalText = btn.innerHTML;
            btn.disabled = true; btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';

            try {
                const payload = {
                    fecha: document.getElementById('h_fecha').value,
                    observacion: document.getElementById('h_observacion').value || null,
                    categoria_hito: parseInt(document.getElementById('h_categoria').value),
                    categoria_calendario: parseInt(document.getElementById('h_categoria').value)
                };
                await api.post(`/proyectos/${editingId}/hitos`, payload);
                showToast('Hito guardado exitosamente');
                hideAddHitoForm();
                loadHitos_edit(editingId);
            } catch (error) {
                showToast(error.message, 'error');
            } finally {
                btn.disabled = false; btn.innerHTML = originalText;
            }
        }

        // ==========================================
        // FUNCIONES OBSERVACIONES (Modal EdiciÃ³n)
        // ==========================================
        function showAddObservacionForm() {
            document.getElementById('addObservacionForm').classList.remove('hidden');
            document.getElementById('o_fecha').value = new Date().toISOString().split('T')[0];
        }

        function hideAddObservacionForm() {
            document.getElementById('addObservacionForm').classList.add('hidden');
            document.getElementById('addObservacionForm').reset();
        }

        async function loadObservaciones_edit(pid) {
            const list = document.getElementById('observacionesList');
            if (!list) return;
            list.innerHTML = '<div class="text-center py-2 text-gray-400 text-sm italic"><i class="fas fa-spinner fa-spin mr-2"></i> Cargando observaciones...</div>';

            try {
                const data = await api.get(`/proyectos/${pid}/observaciones`);
                const observaciones = data.observaciones || [];

                if (observaciones.length === 0) {
                    list.innerHTML = '<div class="text-center py-4 bg-gray-50 rounded-lg text-gray-400 text-sm font-medium border border-gray-100">No hay observaciones registradas.</div>';
                    return;
                }

                const htmlContent = observaciones.map(o => {
                    const dateStr = o.fecha ? o.fecha.split('T')[0] : 'Sin fecha';
                    return `
                    <div class="p-3 rounded-lg border border-blue-100 bg-blue-50/30 hover:bg-blue-50/50 transition">
                        <div class="flex justify-between mb-2">
                            <span class="text-[10px] font-bold text-blue-600 bg-blue-100 px-2 py-0.5 rounded-full"><i class="fas fa-calendar mr-1"></i>${dateStr}</span>
                            <span class="text-[10px] text-gray-500"><i class="fas fa-user mr-1"></i> ID:${o.creado_por || '?'}</span>
                        </div>
                        <p class="text-sm text-gray-700 leading-snug break-words whitespace-pre-wrap">${o.observacion}</p>
                    </div>`;
                }).join('');
                list.innerHTML = htmlContent;
            } catch (e) {
                console.error(e);
                list.innerHTML = '<div class="text-center py-2 text-rose-500 text-xs text-medium">Error al cargar observaciones</div>';
            }
        }

        async function saveObservacion_edit(e) {
            e.preventDefault();
            if (!editingId) return;

            const btn = document.getElementById('o_submitBtn');
            const originalText = btn.innerHTML;
            btn.disabled = true; btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';

            try {
                const payload = {
                    fecha: document.getElementById('o_fecha').value,
                    observacion: document.getElementById('o_observacion').value
                };
                await api.post(`/proyectos/${editingId}/observaciones`, payload);
                showToast('ObservaciÃ³n agregada con Ã©xito');
                hideAddObservacionForm();
                loadObservaciones_edit(editingId);
            } catch (error) {
                showToast(error.message, 'error');
            } finally {
                btn.disabled = false; btn.innerHTML = originalText;
            }
        }

        // ==========================================
        // FUNCIONES DOCUMENTOS (Modal EdiciÃ³n)
        // ==========================================
        async function loadDocumentos_edit(pid) {
            const container = document.getElementById('documentosList');
            if (!container) return;
            container.innerHTML = '<div class="col-span-1 md:col-span-2 text-center py-2 text-gray-400 text-sm italic"><i class="fas fa-spinner fa-spin mr-2"></i> Cargando...</div>';

            try {
                const response = await api.get(`/proyectos/${pid}/documentos`);
                // Asegurar que docs en un array (manejo de esquemas directos o anidados con clave 'documentos')
                const docs = Array.isArray(response) ? response : (response.documentos || []);

                if (!docs || docs.length === 0) {
                    container.innerHTML = '<div class="col-span-1 md:col-span-2 text-center py-4 bg-gray-50 rounded-lg text-gray-400 text-sm font-medium border border-gray-100">Sin archivos asociados.</div>';
                    return;
                }

                const htmlContent = docs.map(doc => {
                    return `
                    <div class="flex items-center p-3 border border-gray-200 rounded-lg bg-white shadow-sm hover:shadow transition group relative">
                        <div class="w-10 h-10 rounded-lg bg-gray-50 flex items-center justify-center text-gray-400 shrink-0 border border-gray-100 mr-3">
                            <i class="fas fa-file-${getFileIcon(doc.archivo_nombre || doc.url)} fa-lg"></i>
                        </div>
                        <div class="flex-1 min-w-0 pr-12">
                            <p class="text-sm font-bold text-gray-800 truncate" title="${doc.descripcion || doc.archivo_nombre}">${doc.descripcion || doc.archivo_nombre}</p>
                            <p class="text-[10px] text-gray-400 uppercase font-bold tracking-wider mt-0.5">${doc.tipo_documento || 'Archivo General'}</p>
                        </div>
                        <div class="absolute right-3 opacity-0 group-hover:opacity-100 transition-opacity flex gap-1">
                            <button type="button" onclick="openDocViewer(${doc.id}, '${(doc.archivo_nombre || '').replace(/'/g, "\\'")}')" class="p-1.5 text-gray-500 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition" title="Ver Documento">
                                <i class="fas fa-eye"></i>
                            </button>
                            ${doc.url ? `<a href="${doc.url}" target="_blank" class="p-1.5 text-gray-500 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition" title="Descargar"><i class="fas fa-download"></i></a>` : ''}
                        </div>
                    </div>`;
                }).join('');
                container.innerHTML = htmlContent;
            } catch (e) {
                console.error(e);
                container.innerHTML = '<div class="col-span-2 text-center text-rose-500 text-xs font-bold py-2">Error al leer documentos.</div>';
            }
        }

        async function uploadDocumento_edit(e) {
            if (!editingId) return;
            const file = e.target.files[0];
            if (!file) return;

            const formData = new FormData();
            formData.append('file', file);
            formData.append('tipo_documento', 'Documento General');
            formData.append('descripcion', file.name);

            // Cambiar icon en el boton original temporalmente (opcional si hay UX)
            const label = e.target.parentElement;
            const originInner = label.innerHTML;
            label.innerHTML = '<i class="fas fa-spinner fa-spin mr-1"></i> Subiendo...';
            label.classList.add('cursor-not-allowed', 'opacity-70');

            try {
                await api.post(`/proyectos/${editingId}/documentos/upload`, formData);
                showToast('Archivo respaldado exitosamente');
                loadDocumentos_edit(editingId);
            } catch (error) {
                console.error(error);
                showToast(error.message || 'Error en subida', 'error');
            } finally {
                label.innerHTML = originInner;
                label.classList.remove('cursor-not-allowed', 'opacity-70');
                e.target.value = ''; // clean val
            }
        }
        // ==========================================
        // GESTIÃ“N ASISTIDA (AUDITORÃA INTEG.: URL -> MODAL -> HIGHLIGHT)
        // ==========================================
        function handleAuditParams() {
            const urlParams = new URLSearchParams(window.location.search);
            const pid = parseInt(urlParams.get('pid'));
            const fieldId = urlParams.get('audit_field');

            if (!pid) return;

            console.log(`[Audit] Detectada peticiÃ³n para Proyecto #${pid}, Campo: ${fieldId}`);
            
            // Buscar el proyecto en la lista actual
            const proyecto = proyectos.find(p => p.id === pid);
            if (!proyecto) {
                showToast('Proyecto de auditorÃ­a no encontrado en el listado', 'warning');
                return;
            }

            // Abrir el modal de ediciÃ³n
            editProject(pid);

            // Si hay un campo especÃ­fico, resaltarlo despuÃ©s de que el modal estÃ© listo
            if (fieldId) {
                setTimeout(() => {
                    const target = document.getElementById(fieldId);
                    if (target) {
                        target.scrollIntoView({ behavior: 'smooth', block: 'center' });
                        target.classList.add('audit-highlight');
                        
                        // Agregar un mensaje flotante cerca del campo
                        const helpText = document.createElement('div');
                        helpText.className = 'text-amber-600 text-xs font-bold mt-1 animate-bounce';
                        helpText.innerHTML = '<i class="fas fa-exclamation-triangle mr-1"></i> Este campo requiere su atenciÃ³n segÃºn el reporte de auditorÃ­a.';
                        target.parentNode.appendChild(helpText);

                        // Remover highlight al enfocar o cambiar
                        target.addEventListener('focus', () => {
                            target.classList.remove('audit-highlight');
                            helpText.remove();
                        }, { once: true });

                        // Inyectar botÃ³n de retorno flotante (en caso de que se haya abierto en la misma pestaÃ±a)
                        const backBtn = document.createElement('button');
                        backBtn.id = 'auditBackBtn';
                        backBtn.className = 'fixed bottom-8 left-8 z-[100] px-6 py-4 bg-slate-900 text-white rounded-2xl shadow-2xl border-2 border-indigo-500 font-black text-sm uppercase tracking-widest animate-fade-in flex items-center gap-3 hover:bg-slate-800 transition-all transform hover:-translate-y-1';
                        backBtn.innerHTML = '<i class="fas fa-arrow-left"></i> Volver al Reporte PDF';
                        backBtn.onclick = () => {
                            if (window.history.length > 1) window.history.back();
                            else window.close();
                        };
                        document.body.appendChild(backBtn);

                    } else {
                        console.warn(`[Audit] Campo '${fieldId}' no encontrado en el formulario.`);
                    }
                }, 800); // Esperar a que el modal y la carga de datos (hitos/etc) terminen
            }
        }

        // Limpieza de UI de auditorÃ­a al cerrar modal
        function clearAuditUI() {
            const btn = document.getElementById('auditBackBtn');
            if (btn) btn.remove();
            
            // Limpiar parÃ¡metros de la URL sin recargar para no disparar de nuevo la lÃ³gica
            const url = new URL(window.location);
            url.searchParams.delete('pid');
            url.searchParams.delete('audit_field');
            window.history.replaceState({}, '', url);
        }

        // Interceptar cierre de modal para limpiar UI de auditoria
        const originalCloseModal = closeModal;
        window.closeModal = function() {
            clearAuditUI();
            originalCloseModal();
        };

