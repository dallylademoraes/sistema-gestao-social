# Textos e modelos dos termos (ASAP)

O backend gera os PDFs de **LGPD** e **uso de imagem** no novo cadastro (com dados do titular e assinatura digitalizada).

## Prioridade: modelo PDF (recomendado para texto idêntico ao papel)

Coloque os PDFs oficiais na pasta **`backend/assets/termos/`** (a mesma pasta deste README). O backend procura, por ordem, um destes nomes (maiúsculas/minúsculas não importam):

**LGPD (prioridade):** `Termo LGPD — ASAP.pdf` (ou o mesmo nome com hífen `-` em vez de travessão), depois `modelo_lgpd.pdf`, `termo_lgpd.pdf`, `termo-lgpd.pdf`, `termo_lgpd_modelo.pdf`

**Uso de imagem (prioridade):** `Termo de uso de imagem — ASAP.pdf` (ou com hífen `-`), depois `modelo_imagem.pdf`, `termo_imagem.pdf`, `termo_uso_imagem.pdf`, `termo-uso-imagem.pdf`, `termo_uso_de_imagem.pdf`

Se na pasta houver **apenas um** PDF cujo nome deixa claro o tipo (ex.: só “LGPD” no nome do ficheiro), esse ficheiro é usado como modelo desse termo.

Se existir um ficheiro correspondente ao termo, o sistema **preenche o PDF oficial** nos espaços do formulário (nome, documentos, morada, data, assinatura), **sem** acrescentar páginas extra nem o layout ReportLab da ASAP.

Isto aplica-se aos modelos planos **«Termo LGPD — ASAP»** (2 páginas; dados na última) e **«Termo de uso de imagem — ASAP»** (1 página). Se o PDF tiver outro layout (outra instituição), o sistema tenta o preenchimento; se não reconhecer o formato, usa o modo antigo (modelo + anexo ReportLab).

Os ficheiros `texto_lgpd.txt` / `texto_imagem.txt` só são usados quando **não** há modelo PDF reconhecido.

## Alternativa: só ficheiros de texto

Se nenhum dos PDFs listados acima existir na pasta, o sistema monta o PDF completo em ReportLab a partir de:

- `texto_lgpd.txt`
- `texto_imagem.txt`

1. Copie o texto integral dos documentos oficiais da ASAP para estes ficheiros, em **UTF-8**.
2. Separe parágrafos com **uma linha em branco** para melhor leitura no PDF.
3. Os ficheiros `.txt` incluídos no repositório são **marcadores de exemplo** — substitua pelo texto jurídico aprovado.

## Nota importante

Se o PDF tiver outro nome, renomeie para um da lista acima (por exemplo os ficheiros **Termo LGPD — ASAP** e **Termo de uso de imagem — ASAP** já são reconhecidos), ou faça uma cópia com um desses nomes — só assim o sistema trata como modelo.

Após alterar ficheiros em `assets/termos/`, reinicie o Uvicorn em desenvolvimento.

Os termos são aceites no formulário de **novo cadastro**, com assinatura em canvas; os PDFs finais são gravados automaticamente junto ao cadastro.
