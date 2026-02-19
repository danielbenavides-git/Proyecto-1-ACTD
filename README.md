# Analítica de Datos Saber 11 — Caldas

**Curso:** Analítica Computacional para la Toma de Decisiones | **Profesor:** Juan F. Pérez | **GRUPO 6**

## Equipo
| Nombre | Código |
|---|---|
| Daniel Benavides | 202220428 |
| Juanita Cortés | 202222129 |
| Andrés Felipe Herrera | 202220888 |

## Descripción
Producto de analítica sobre los resultados de las pruebas Saber 11 en el departamento de Caldas, orientado al Ministerio de Educación como usuario final. El análisis busca responder tres preguntas de negocio: (1) cómo varía el desempeño según estrato socioeconómico y nivel educativo de los padres, (2) qué municipios presentan bajo rendimiento y en qué medida el tipo de colegio y la zona rural/urbana lo explican, y (3) si existen brechas de género en matemáticas y lectura crítica entre municipios.

## Ejecución
El producto final es un tablero interactivo desarrollado en **Dash** y desplegado en **AWS EC2**. Para correrlo localmente, instalar dependencias con `pip install -r despliegue/requirements.txt` y ejecutar `python despliegue/app.py`. Los datos fueron extraídos del portal [Datos Abiertos Colombia]([https://www.datos.gov.co/Educaci-n/Resultados-nicos-Saber-11/kgxf-xxbe](https://www.datos.gov.co/Educaci-n/Resultados-nicos-Saber-11/kgxf-xxbe/data_preview)) usando AWS Glue y Athena.
