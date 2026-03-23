# Geoportal Municipal - Algarrobo

> Plataforma integral de gestión geoespacial y administrativa para la Ilustre Municipalidad de Algarrobo.

## ¿Qué hace esta aplicación?

El Geoportal Municipal es una solución diseñada para centralizar y optimizar la gestión de datos territoriales, proyectos y documentación de la municipalidad. Permite a los distintos departamentos (como SECPLAN o la Dirección de Obras) acceder a información crítica de manera estructurada y visual.

Entre sus funcionalidades principales destacan el control de auditoría detallado de todas las acciones del sistema, la gestión de proyectos municipales con seguimiento de avance, y un robusto sistema de procesamiento de documentos. Este último incluye la capacidad de extraer texto mediante OCR (Reconocimiento Óptico de Caracteres), lo que permite indexar y buscar información dentro de archivos PDF, Word o imágenes escaneadas. Además, integra un componente de mapas para la visualización espacial de los proyectos y activos de la comuna.

## Inicio Rápido

Para poner en marcha el proyecto en un entorno local, sigue estos comandos mínimos:

```bash
# 1. Preparar el Backend
cd backend
pip install -r requirements.txt
cp .env.example .env # Configurar con valores reales

# 2. Levantar el servidor
python app21.py
```

*Nota: Para el frontend basta con servir la carpeta `frontend/` mediante cualquier servidor de archivos estáticos (Live Server, Nginx, etc).*

## Estructura del Proyecto

```
ALGARROBO_BASE2/
├── backend/            # API Flask, servicios de procesamiento y lógica de negocio
├── frontend/           # Interfaz de usuario (HTML, Vanilla JS, Tailwind)
│   ├── division/       # Vistas específicas por departamento (secplan, obras, etc.)
│   ├── script/         # Lógica de cliente, ruteo y consumo de API
│   └── assets/         # Recursos estáticos e imágenes
├── database/           # Scripts SQL, triggers y definiciones de esquema
├── movil/              # Directorio destinado a la aplicación móvil
├── docs/               # Almacenamiento local de documentos procesados
└── transversal/        # Recursos y consultas compartidas
```

## Documentación Detallada

- 📦 [Tecnologías utilizadas](./TECNOLOGIAS.md)
- 🚀 [Guía de instalación completa](./INSTALACION.md)

## Estado del Proyecto

| Aspecto | Estado |
|---|---|
| Versión | 2.1.0 (Inferida de backend/app21.py) |
| Entorno de desarrollo | ✅ Funcional |
| Tests | ⚠️ Parcial — Scripts de prueba básicos en raíz |
