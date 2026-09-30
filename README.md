# toyosu-campus-blender

芝浦工業大学 豊洲キャンパスを Blender で作るプロジェクト。外観（全棟）と、建物の中（廊下など）を作る。

- Blender 5.2
- 大学の公式プロジェクトではなく、個人の制作

## 中身
| パス | 内容 |
|---|---|
| `toyosu_campus.blend` | メインの Blender ファイル |
| `scripts/` | Blender の中で実行して形を作るスクリプト |
| `renders/` | 確認用のレンダー画像 |
| `image/` | 参考資料の一覧（`image/README.md`）、座標変換・検証のスクリプトとデータ |
| `制作メモ.md` | 座標のルール、推定した寸法、検証の結果、次にやること |

## 参考資料について
大学公式サイトの写真や学会の案内図など、他人が著作権を持つ資料はリポジトリに入れていない。
入手元と取り直し方は `image/README.md` にある。

## データの出典
- 3D都市モデル：国土交通省 Project PLATEAU（CC BY 4.0）
- 建物の形・道路：© OpenStreetMap contributors（ODbL）
- 航空写真：国土地理院（地理院タイル）
