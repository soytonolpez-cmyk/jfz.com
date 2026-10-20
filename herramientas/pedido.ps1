# ============================================================
#  pedido.ps1 — copia los ORIGINALES (RAW/CR2/JPG) de un pedido
#  desde por-procesar\ hacia una carpeta "pedido-fecha-hora".
# ============================================================
# normalmente NO necesitas este archivo: el boton
# «Descargar pedido (.ps1)» del carrito genera uno igual, ya
# relleno con las fotos del pedido. Este es el modelo manual.
#
# USO (PowerShell, dentro de la carpeta del proyecto):
#   powershell -ExecutionPolicy Bypass -File herramientas\pedido.ps1 IMG_1468 IMG_6006
#   (los nombres van SIN extension: sirve IMG_1468.CR2 como .JPG)
#
# Si no pasas nombres, usa esta lista:
$NombresPedido = @(
  # "IMG_1468",
  # "IMG_6006"
)

$Raiz     = Split-Path -Parent $PSScriptRoot          # carpeta del proyecto
$Origenes = Join-Path $Raiz 'por-procesar'            # donde viven tus originales
$Destino  = Join-Path $Raiz ('pedido-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))

$nombres = if ($args.Count -gt 0) { $args } elseif ($NombresPedido.Count -gt 0) { $NombresPedido } else { Write-Host 'Escribe los nombres en $NombresPedido o pásalos como argumentos (ej: ... IMG_1468 IMG_6006)' -ForegroundColor Yellow; return }

New-Item -ItemType Directory -Force -Path $Destino | Out-Null
$encontrados = 0; $faltan = @()
foreach ($n in $nombres) {
  $hit = $null
  if (Test-Path $Origenes) {
    $hit = Get-ChildItem -LiteralPath $Origenes -Recurse -File | Where-Object { $_.BaseName -ieq $n } | Select-Object -First 1
  }
  if (-not $hit) {
    # respaldo: busca en todo el proyecto (ignorando los WebP publicados)
    $hit = Get-ChildItem -LiteralPath $Raiz -Recurse -File | Where-Object { $_.BaseName -ieq $n -and $_.Extension -notin '.webp','.html','.js','.css','.md' } | Select-Object -First 1
  }
  if ($hit) { Copy-Item -LiteralPath $hit.FullName -Destination $Destino -Force; $encontrados++; Write-Host "OK   $n -> $($hit.Name)" -ForegroundColor Green }
  else { $faltan += $n; Write-Host "FALTA $n (no hay original en $Origenes)" -ForegroundColor Yellow }
}
Write-Host ''
Write-Host "$encontrados originales copiados a: $Destino"
if ($faltan.Count) { Write-Host "Faltaron $($faltan.Count): $($faltan -join ', ')" -ForegroundColor Yellow }
explorer $Destino
