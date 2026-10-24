"""Render original PDF evidence or QA pages without changing the source PDF."""
import argparse
from pathlib import Path
import sys
import pymupdf

def main():
    print(f'Python executable: {sys.executable}')
    parser=argparse.ArgumentParser()
    parser.add_argument('source',type=Path)
    parser.add_argument('output',type=Path)
    parser.add_argument('--page',type=int)
    parser.add_argument('--clip',nargs=4,type=float)
    args=parser.parse_args()
    with pymupdf.open(args.source) as pdf:
        if args.page:
            args.output.parent.mkdir(parents=True,exist_ok=True)
            pdf[args.page-1].get_pixmap(dpi=220,clip=pymupdf.Rect(args.clip) if args.clip else None,
                                      colorspace=pymupdf.csGRAY,alpha=False).save(args.output)
        else:
            args.output.mkdir(parents=True,exist_ok=True)
            for i,page in enumerate(pdf,1):
                page.get_pixmap(dpi=130,alpha=False).save(args.output/f'page-{i:02d}.png')
            print(f'Rendered {len(pdf)} pages')

if __name__=='__main__': main()
