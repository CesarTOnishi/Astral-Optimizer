# Astral Optimizer

O aplicativo usa um ícone próprio, abertura animada e um indicador discreto de
sincronização na barra lateral para tarefas executadas em segundo plano.

Aplicativo PySide6 para consultar builds públicas de Honkai: Star Rail pelo
UID. O DPS Benchmark e os atributos em combate usam o motor do
[Fribbels HSR Optimizer](https://github.com/fribbels/hsr-optimizer).

## Requisitos

- Python 3.11 ou superior
- Node.js 26 ou superior para recompilar o motor
- npm 11 ou superior

## Instalação

Clone o projeto incluindo o motor Fribbels configurado como submódulo:

```powershell
git clone --recurse-submodules https://github.com/CesarTOnishi/Astral-Optimizer.git
cd Astral-Optimizer
```

Se o projeto já foi clonado sem os submódulos, execute:

```powershell
git submodule update --init --recursive
```

Depois instale e inicie o aplicativo:

```powershell
python -m pip install -r requirements.txt
powershell -ExecutionPolicy Bypass -File scripts/build_fribbels_engine.ps1
python honkai.py
```

O motor compilado fica em
`third_party/fribbels-hsr-optimizer/.honkai-engine/benchmark-engine.js`.
O script copia automaticamente a ponte mantida pelo Astral Optimizer para o
submódulo antes da compilação; não é necessário alterar o Fribbels manualmente.
Durante a consulta, a interface mostra primeiro o fallback local e o substitui
assincronamente pelo resultado oficial do Fribbels.

## Criar o executável no Windows

Depois de compilar o motor Fribbels, instale o PyInstaller e execute a receita
de empacotamento:

```powershell
python -m pip install pyinstaller
powershell -ExecutionPolicy Bypass -File scripts/build_fribbels_engine.ps1
powershell -ExecutionPolicy Bypass -File scripts/build_executable.ps1
```

O aplicativo portátil será criado em `AstralOptimizer\AstralOptimizer.exe`.
O pacote já inclui o Node.js usado pelo benchmark; quem receber essa pasta não
precisa instalar Python, Node.js ou as dependências do projeto.

## Sincronização em segundo plano

Consultas de UID, atualização do catálogo, benchmark, verificação de novas
versões e backup no Google Drive usam workers separados da interface. O estado
aparece no rodapé da barra lateral como sincronizando, concluído ou com falha;
se houver mais de uma tarefa, o contador também é exibido.

Durante uma consulta, a pesquisa de UID continua disponível. Se outra UID for
pesquisada antes do fim, ela entra na fila como a próxima consulta e um resultado
anterior não substitui a conta solicitada mais recentemente. Apenas a instalação
de uma atualização bloqueia a janela, para evitar interromper a troca de arquivos.

## Versões e atualização automática

A versão atual fica em `APP_VERSION`, dentro de `app/config.py`, e aparece nas
configurações abertas pela engrenagem. O aplicativo consulta em segundo plano a
Release mais recente de `CesarTOnishi/Astral-Optimizer` no GitHub. A consulta
automática ocorre no máximo uma vez a cada seis horas; também existe um botão
para verificar manualmente.

Para preparar os arquivos de uma nova Release, atualize `APP_VERSION`, recrie o
executável e execute:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/package_release.ps1
```

Depois crie uma Release com a tag correspondente, como `v1.1.0`, e anexe os
dois arquivos gerados em `release`: o ZIP e o `.sha256`. No executável Windows,
o app valida, extrai e instala o ZIP após a confirmação do usuário, reiniciando
em seguida. Bancos, login e configurações permanecem em
`%LOCALAPPDATA%\AstralOptimizer` e não são substituídos.

## Perfis locais

O aplicativo permite criar um perfil com nome de usuário, e-mail e senha. É
possível entrar usando o nome de usuário ou o e-mail. As contas
ficam somente no computador, em `%LOCALAPPDATA%\AstralOptimizer`. Na primeira
execução, instalações existentes são copiadas de `%LOCALAPPDATA%\HonkaiBuilds`
para preservar login, UID e histórico anteriores.
As senhas são protegidas com PBKDF2-SHA256, salt aleatório e 600.000 iterações;
a senha original nunca é armazenada. O perfil pode ser encerrado pela
engrenagem exibida no rodapé da barra lateral após o login.

O acompanhamento de Saltos é isolado por perfil local. Cada perfil pode
importar uma ou mais contas do jogo e alternar entre os UIDs pelo seletor
“Conta do jogo”; pity, garantidos e histórico nunca são misturados entre
perfis ou UIDs.

Nas configurações do perfil também é possível salvar uma UID principal. Ela é
carregada ao abrir “Conta”, sem preencher o campo de pesquisa.
A pesquisa da tela inicial permite consultar outras contas sem substituir a
UID salva. O DPS Benchmark fica integrado às Builds e também aparece ao abrir
a conta principal. A opção “Rank” abre, no navegador padrão,
o perfil público da UID principal no SeeleLand. O aplicativo não copia nem
armazena os rankings desse serviço externo.

## Planejador de tiros

A opção “Planejador” lê automaticamente o pity e a garantia dos banners
limitados de personagem e Cone de Luz a partir do histórico importado. Jades
Estelares, Passes Especiais, Luz Estelar, cashback estimado e a ordem desejada
entre eidolons e Cone de Luz são salvos por perfil. A tabela mostra a chance e
a média de tiros para cada objetivo de E0S0 até E6S5. O cálculo usa as
distribuições de soft pity, taxas consolidadas e os
níveis de reembolso de 0%, 4%, 7,5% e 11% adotados pelo Fribbels. A página
mostra os tiros totais, a chance de sucesso e o custo médio de cada objetivo.
Essas configurações também entram no backup do Google Drive.

## Inventário de relíquias

A opção “Relíquias” salva localmente todas as peças encontradas nos personagens
do Showcase da UID principal. Novas consultas atualizam o portador atual sem
apagar as peças vistas anteriormente. A tela mostra o personagem atual e, quando
uma peça foi movida ou deixou de aparecer, o portador anterior. As peças são
ordenadas automaticamente da maior para a menor pontuação. Também há filtros
por personagem, situação, parte e conjunto, além de opções de ordenação por
pontuação, atualização recente ou nome do personagem.

## Catálogo de personagens e Cones de Luz

A opção “Personagens e Cones” funciona sem UID e apresenta pesquisa, filtros
por Caminho e raridade, atributos no nível 80, habilidades, Rastros, eidolons e
efeitos de sobreposição S1–S5. Nos personagens, Kit principal, Rastros e
Eidolons ficam separados em guias. O catálogo básico reutiliza os dados e imagens já
presentes no Fribbels. Ao abrir a página pela primeira vez ou selecionar
“Atualizar catálogo”, os detalhes em português são sincronizados do
StarRailRes e guardados em `%LOCALAPPDATA%\AstralOptimizer\catalog`.

A atualização é atômica: arquivos incompletos não substituem a última versão
válida. Imagens obtidas pela internet são armazenadas em cache local, enquanto
personagens mais recentes ausentes na fonte continuam aparecendo pelo fallback
do Fribbels.

## Importação do histórico de Saltos

Na aba “Saltos”, o botão “Importar arquivo” aceita:

- o arquivo `data_*` do cache do jogo;
- backups `.xlsx` exportados pelo Star Rail Station.

Para importar um Excel, entre em um perfil e defina primeiro a UID principal
nas configurações. O aplicativo lê os banners de personagem, cone de luz,
Salto Estelar e Novatos. Os banners são separados como “Salto Hiperespacial de
Colaboração de Personagem” e “Salto Hiperespacial de Colaboração de Cone de
Luz”. Quando o Excel contém apenas o resumo da colaboração, o app
salva seus totais, pities e 5★ conhecidos separadamente, sem fabricar linhas
de histórico ausentes.

## Backup no Google Drive

Na engrenagem do perfil, a seção “Backup no Google Drive” permite conectar uma
conta Google, salvar imediatamente, restaurar e desconectar. Depois da conexão,
cada importação de Saltos envia automaticamente um backup JSON privado para a
pasta de dados do aplicativo (`appDataFolder`). O token OAuth fica no
gerenciador de credenciais do sistema; a senha do Google nunca passa pelo app.

Para habilitar a conexão durante o desenvolvimento:

1. crie um projeto no Google Cloud e ative a Google Drive API;
2. configure a tela de consentimento OAuth;
3. crie um cliente OAuth do tipo “Aplicativo para computador”;
4. baixe o JSON como `google_oauth_client.json` na raiz do projeto;
5. instale novamente as dependências de `requirements.txt`.

O arquivo OAuth é ignorado pelo Git. Também é possível indicar outro caminho
pela variável `ASTRAL_GOOGLE_CREDENTIALS`.

## Terceiros

Consulte [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). Fribbels HSR
Optimizer é distribuído sob a licença MIT. Os dados sincronizados do
StarRailRes possuem aviso próprio em `THIRD_PARTY_NOTICES.md`. Este projeto não
é afiliado à HoYoverse, ao Fribbels, ao SeeleLand ou à Enka.Network.
