#!/bin/bash
cd "c:\Users\ASUS\OneDrive\Documentos\Proyect"

# Limpiar secretos de Google OAuth del historial
git filter-branch --force --tree-filter '
  find . -name "*.py" -o -name "*.md" | while read file; do
    if [ -f "$file" ]; then
      sed -i "s/812955308663-htj55eqsni45mvhtl10gp0bioaoiptkg\.apps\.googleusercontent\.com/REDACTED_GOOGLE_CLIENT_ID/g" "$file"
      sed -i "s/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/REDACTED_GOOGLE_CLIENT_SECRET/g" "$file"
    fi
  done
' -- --all
