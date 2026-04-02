# ZQ-CloudFlareScan (ipv4&ipv6)  



🚀 高效扫描：自动从 CloudFlare 官方 IP 段生成 IP 地址

📊 双模式测速：完全测速 + 地区测速，满足不同需求

🌍 全球覆盖：内置全球大部分机场IATA代码映射，自动识别地区

⚡ 异步处理：支持高并发测试，快速获取结果

📋 一键复制：双击表格单元格即可复制内容

📈 实时统计：显示扫描进度、速度

🔄 GitHub Actions：支持自动化定时扫描，结果自动提交到仓库

## 使用方法

### GUI 版本
- win-X64 直接下载使用
- macOS arm 安装提前 需要将安全性与隐私里-选择允许从任何来源
  - 终端输入命令：`sascript -e 'do shell script "sudo spctl --master-disable" with administrator privileges'`

### GitHub Actions 自动化扫描

#### 触发方式
1. **手动触发**：在仓库 Actions 页面点击 "Run workflow"
2. **定时触发**：每天 UTC 0 点自动运行

#### 可选参数
- **IATA 码**：（可选）指定地区码进行测速，例如 LAX（洛杉矶）、SJC（圣何塞）、HKG（香港）等

#### 使用步骤
1. 将代码推送到 GitHub 仓库
2. 进入仓库的 **Actions** 标签页
3. 选择 **"Cloudflare Scan"** workflow
4. 点击 **"Run workflow"** 按钮（可选择填写 IATA 码）
5. 等待扫描完成，`ipv4.csv` 和 `ipv6.csv` 将自动提交到仓库

#### 常见 IATA 码
- HKG：香港
- NRT：东京成田
- LAX：洛杉矶
- SJC：圣何塞
- SEA：西雅图
- ORD：芝加哥
- ATL：亚特兰大
- FRA：法兰克福
- AMS：阿姆斯特丹



