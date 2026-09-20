\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{graduate-modeling}[2026/08/16 Graduate mathematical modeling paper]

% 本模板只支持 XeLaTeX：ctexart + xeCJK 字体选择、\setCJKmainfont 与
% \IfFontExistsTF 回退均依赖 XeTeX。用 pdflatex/lualatex 编译不是"缺字"，
% 而是不受支持，因此在此直接给出可读错误而不是让排版静默走偏。
\RequirePackage{iftex}
\ifXeTeX\else
  % 帮助文本保持纯 ASCII：报错时引擎正是非 XeTeX 的那一个，
  % 此时 .cls 里的中文字面量本身会再触发 "Unicode character not set up"，
  % 反而盖掉这条本来要给出的可读信息。
  \ClassError{graduate-modeling}
    {This class requires XeLaTeX}
    {Compile with xelatex via: python scripts/compile_paper.py <project-dir>/<paper-dir>.
     pdflatex and lualatex are not supported by this template.}
\fi

\newif\ifgmcontinuousnumbers
\DeclareOption{continuousnumbers}{\gmcontinuousnumberstrue}
\DeclareOption{bodyresetnumbers}{\gmcontinuousnumbersfalse}
\DeclareOption*{\PassOptionsToClass{\CurrentOption}{ctexart}}
\ExecuteOptions{bodyresetnumbers}
\ProcessOptions\relax

\LoadClass[UTF8,a4paper,zihao=-4]{ctexart}

\RequirePackage{geometry}
\geometry{top=30mm,bottom=25mm,left=22.5mm,right=22.5mm}
\RequirePackage{setspace}
\setstretch{1.20}
\RequirePackage{amsmath,amssymb,bm}
\RequirePackage{booktabs,longtable,tabularx,array,multirow}
\RequirePackage{graphicx,float,caption,subcaption}
\RequirePackage{enumitem}
\RequirePackage{xcolor}
\RequirePackage{listings}
\RequirePackage{fancyhdr}
\RequirePackage{hyperref}
\RequirePackage[ruled,vlined,linesnumbered]{algorithm2e}
\RequirePackage{needspace}
\RequirePackage{etoolbox}

% Windows 存在常用中文字体时使用；否则保留 ctex 针对当前平台选择的
% 默认 CJK fontset，避免把未安装的 Fandol family name 强行写死。
\IfFontExistsTF{SimSun}{\setCJKmainfont{SimSun}}{}
\IfFontExistsTF{SimHei}{\setCJKsansfont{SimHei}}{}
\IfFontExistsTF{KaiTi}{\setCJKmonofont{KaiTi}}{}
\IfFontExistsTF{Times New Roman}{%
  \setmainfont{Times New Roman}%
}{%
  \IfFontExistsTF{TeX Gyre Termes}{%
    \setmainfont{TeX Gyre Termes}%
  }{%
    \IfFontExistsTF{Libertinus Serif}{\setmainfont{Libertinus Serif}}{}%
  }%
}

\pagestyle{fancy}
\fancyhf{}
\renewcommand{\headrulewidth}{0pt}
\fancyfoot[C]{\thepage}

\ctexset{
  section={format=\centering\heiti\zihao{4},name={,},number=\arabic{section}.},
  subsection={format=\heiti\zihao{-4},name={,},number=\thesection.\arabic{subsection}},
  subsubsection={format=\heiti\zihao{-4},name={,},number=\thesubsection.\arabic{subsubsection}}
}
\pretocmd{\section}{\Needspace{4\baselineskip}}{}{}
\pretocmd{\subsection}{\Needspace{3\baselineskip}}{}{}
\pretocmd{\subsubsection}{\Needspace{3\baselineskip}}{}{}

\captionsetup{font=small,labelsep=quad}
\setlength{\parindent}{2em}
\setlength{\parskip}{0pt}
\setlist{nosep,leftmargin=2.5em}
\hypersetup{colorlinks=false,pdfborder={0 0 0},bookmarksnumbered=true}
\graphicspath{{../求解/}}

\lstset{
  basicstyle=\ttfamily\small,
  breaklines=true,
  frame=single,
  numbers=left,
  numberstyle=\tiny,
  showstringspaces=false,
  tabsize=4
}

\SetAlgorithmName{算法}{算法}{算法目录}
\SetKwInput{KwIn}{输入}
\SetKwInput{KwOut}{输出}
\SetKw{Return}{返回}
\SetAlgoCaptionSeparator{：}
\SetAlFnt{\small}
\SetAlCapFnt{\small\bfseries}

\newcommand{\modelingfrontmatter}{%
  \ifgmcontinuousnumbers\pagestyle{fancy}\else\pagestyle{empty}\fi}
\newcommand{\modelingmainmatter}{%
  \clearpage\pagestyle{fancy}%
  \ifgmcontinuousnumbers\else\setcounter{page}{1}\fi}

\newenvironment{competitionabstract}
  {\begin{center}\heiti\zihao{4} 摘\quad 要\end{center}\vspace{0.5em}}
  {\par}

\newcommand{\keywords}[1]{\par\vspace{0.8em}\noindent\textbf{关键词：}#1}
\newcommand{\papertitle}[1]{
  \begin{center}
    {\heiti\zihao{3}\bfseries #1\par}
  \end{center}
  \vspace{0.8em}
}
