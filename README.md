# Aerodynamics-Code

軌道シミュレーション用 GUI ツールです。

## ビルド方法

このプロジェクトは `uv` で管理されています。
`uv sync` で仮想環境をインストールできます。

### Nuitka

Nuitkaでは以下のコマンドでexeファイル化できます。
WindowsではDefenderによってbuild時にファイルが削除される場合があるため、適宜ウイルスチェックから弾いてください。
```powershell
uv run nuitka --standalone --enable-plugin=pyside6 --include-data-dir=icons=icons main.py
```

ビルド結果は `main.dist` フォルダに出力されます。
起動する際は `main.dist/main.exe` を実行してください。


### PyInstaller

`main.spec` で `icons` ディレクトリや `pyqtgraph` のデータファイルを同梱する設定をしています。スタンドアロン版を作成するには次のコマンドを実行します。

```powershell
uv run pyinstaller --clean --noconfirm main.spec
```

ビルド結果は `dist/main` フォルダに配置されます。起動する際は `dist/main/main.exe` を利用してください。
