\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{graduate-modeling}[2026/08/16 Graduate mathematical modeling paper]

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

\IfFontExistsTF{SimSun}{\setCJKmainfont{SimSun}}{\setCJKmainfont{FandolSong-Regular}}
\IfFontExistsTF{SimHei}{\setCJKsansfont{SimHei}}{\setCJKsansfont{FandolHei-Regular}}
\IfFontExistsTF{KaiTi}{\setCJKmonofont{KaiTi}}{\setCJKmonofont{FandolKai-Regular}}
\IfFontExistsTF{Times New Roman}{\setmainfont{Times New Roman}}{\setmainfont{TeX Gyre Termes}}

\pagestyle{fancy}
\fancyhf{}
\renewcommand{\headrulewidth}{0pt}
\fancyfoot[C]{\thepage}

\ctexset{
  section={format=\centering\heiti\zihao{4},name={,},number=\arabic{section}.},
  subsection={format=\heiti\zihao{-4},name={,},number=\thesection.\arabic{subsection}},
  subsubsection={format=\heiti\zihao{-4},name={,},number=\thesubsection.\arabic{subsubsection}}
}

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

\newenvironment{competitionabstract}
  {\thispagestyle{plain}\begin{center}\heiti\zihao{3} 摘\quad 要\end{center}\vspace{0.5em}}
  {\par}

\newcommand{\keywords}[1]{\par\vspace{0.8em}\noindent\textbf{关键词：}#1}
\newcommand{\papertitle}[1]{
  \begin{center}
    {\heiti\zihao{2}\bfseries #1\par}
  \end{center}
  \vspace{0.8em}
}
