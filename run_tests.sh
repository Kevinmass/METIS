#!/bin/bash

# Script para ejecutar todos los tests de METIS
# Ejecuta: unitarios, lint (ruff + black), integración y e2e
# Los logs se guardan en la carpeta raíz del proyecto

echo "🧪 Ejecutando suite completa de tests de METIS..."
echo ""

# Verificar que estamos en el directorio correcto
if [ ! -f "pyproject.toml" ]; then
    echo "❌ Ejecutar desde el directorio raíz de METIS"
    exit 1
fi

# Fecha para referencia en logs
FECHA=$(date +"%Y-%m-%d %H:%M:%S")
echo "📅 Fecha de ejecución: $FECHA"
echo ""

# ============================================================================
# 1. TESTS UNITARIOS
# ============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔬 1/5 — Tests Unitarios"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
{
    echo "=========================================="
    echo "TESTS UNITARIOS — $FECHA"
    echo "=========================================="
    pytest tests/unit/ -v 2>&1
} > UnitTestLog.txt
UNIT_EXIT=$?
if [ $UNIT_EXIT -eq 0 ]; then
    echo "✅ Tests unitarios: PASARON (exit 0)"
else
    echo "❌ Tests unitarios: FALLARON (exit $UNIT_EXIT)"
fi
echo ""

# ============================================================================
# 2. RUFF LINTER
# ============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔍 2/5 — Ruff Linter (check --fix)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
{
    echo "=========================================="
    echo "RUFF CHECK — $FECHA"
    echo "=========================================="
    ruff check --fix 2>&1
} > RuffLog.txt
RUFF_EXIT=$?
if [ $RUFF_EXIT -eq 0 ]; then
    echo "✅ Ruff: SIN ERRORES"
else
    echo "⚠️  Ruff: encontró $RUFF_EXIT problema(s) (revisar RuffLog.txt)"
fi
echo ""

# ============================================================================
# 3. BLACK FORMATTER
# ============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎨 3/5 — Black Formatter"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
{
    echo "=========================================="
    echo "BLACK FORMAT — $FECHA"
    echo "=========================================="
    black . 2>&1
} > BlackLog.txt
BLACK_EXIT=$?
if [ $BLACK_EXIT -eq 0 ]; then
    echo "✅ Black: formato aplicado correctamente"
else
    echo "⚠️  Black: error (revisar BlackLog.txt)"
fi
echo ""

# ============================================================================
# 4. TESTS DE INTEGRACIÓN
# ============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔗 4/5 — Tests de Integración"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
{
    echo "=========================================="
    echo "TESTS DE INTEGRACIÓN — $FECHA"
    echo "=========================================="
    python -m pytest tests/integration -q 2>&1
} > IntegrationTestLog.txt
INT_EXIT=$?
if [ $INT_EXIT -eq 0 ]; then
    echo "✅ Tests de integración: PASARON (exit 0)"
else
    echo "❌ Tests de integración: FALLARON (exit $INT_EXIT)"
fi
echo ""

# ============================================================================
# 5. TESTS E2E
# ============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🌐 5/5 — Tests End-to-End"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
{
    echo "=========================================="
    echo "TESTS E2E — $FECHA"
    echo "=========================================="
    pytest tests/e2e/ -v 2>&1
} > E2ETestLog.txt
E2E_EXIT=$?
if [ $E2E_EXIT -eq 0 ]; then
    echo "✅ Tests E2E: PASARON (exit 0)"
else
    echo "❌ Tests E2E: FALLARON (exit $E2E_EXIT)"
fi
echo ""

# ============================================================================
# RESUMEN
# ============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 RESUMEN"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Unitarios:    $([ $UNIT_EXIT -eq 0 ] && echo '✅ OK' || echo '❌ FAIL')"
echo "  Ruff:         $([ $RUFF_EXIT -eq 0 ] && echo '✅ OK' || echo '⚠️  ISSUES')"
echo "  Black:        $([ $BLACK_EXIT -eq 0 ] && echo '✅ OK' || echo '⚠️  ERROR')"
echo "  Integración:  $([ $INT_EXIT -eq 0 ] && echo '✅ OK' || echo '❌ FAIL')"
echo "  E2E:          $([ $E2E_EXIT -eq 0 ] && echo '✅ OK' || echo '❌ FAIL')"
echo ""
echo "📄 Logs guardados:"
echo "  UnitTestLog.txt"
echo "  RuffLog.txt"
echo "  BlackLog.txt"
echo "  IntegrationTestLog.txt"
echo "  E2ETestLog.txt"
echo ""

# Exit code general: falla si alguno falló
TOTAL_FAIL=$(( (UNIT_EXIT != 0) + (RUFF_EXIT != 0) + (INT_EXIT != 0) + (E2E_EXIT != 0) ))
if [ $TOTAL_FAIL -gt 0 ]; then
    echo "⚠️  $TOTAL_FAIL conjunto(s) de tests con problemas. Revisar logs."
    exit 1
else
    echo "🎉 ¡Todos los tests pasaron!"
    exit 0
fi