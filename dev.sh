#!/bin/bash

# Script para desarrollo local de METIS
# Arranca API y frontend en background

echo "🚀 Iniciando METIS para desarrollo local..."

# Verificar que estamos en el directorio correcto
if [ ! -f "pyproject.toml" ]; then
    echo "❌ Ejecutar desde el directorio raíz de METIS"
    exit 1
fi

# Instalar dependencias Python si no están
echo "📦 Verificando dependencias Python..."
pip install -r requirements.txt -r requirements-dev.txt

# Instalar dependencias frontend si no están
echo "📦 Verificando dependencias frontend..."
cd frontend
npm install
cd ..

# Arrancar API en background
echo "🔌 Arrancando API en http://127.0.0.1:8000..."
uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload &
API_PID=$!

# Esperar un poco para que la API inicie
sleep 3

# Arrancar frontend en background
echo "🎨 Arrancando frontend en http://127.0.0.1:5173..."
cd frontend
npm run dev &
FRONTEND_PID=$!

cd ..

echo "✅ Servicios iniciados!"
echo "  - API: http://127.0.0.1:8000/docs"
echo "  - Frontend: http://127.0.0.1:5173"
echo ""
echo "Para detener: kill $API_PID $FRONTEND_PID"
echo "O presiona Ctrl+C"

# Mantener el script corriendo
wait