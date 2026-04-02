#!/usr/bin/env python3
"""
命令行扫描工具
用于执行 IPv4 和 IPv6 扫描并生成 CSV 文件
"""

import sys
import asyncio
import csv
import os
from datetime import datetime
from CloudFlareScan import IPv4Scanner, IPv6Scanner, SpeedTestWorker

class CLI:
    def __init__(self):
        self.results_dir = "results"
        if not os.path.exists(self.results_dir):
            os.makedirs(self.results_dir)
    
    def log(self, message):
        """日志输出"""
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}")
    
    def export_csv(self, results, filename):
        """导出结果到 CSV 文件"""
        if not results:
            self.log(f"没有结果可导出到 {filename}")
            return
        
        filepath = os.path.join(self.results_dir, filename)
        
        try:
            with open(filepath, 'w', newline='', encoding='utf-8-sig') as csvfile:
                fieldnames = ['排名', 'IP地址', '地区码', '地区', '延迟(ms)', '下载速度(MB/s)', '端口', '测速类型']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                
                for i, result in enumerate(results, 1):
                    writer.writerow({
                        '排名': i,
                        'IP地址': result['ip'],
                        '地区码': result.get('iata_code', 'UNKNOWN'),
                        '地区': result.get('chinese_name', '未知地区'),
                        '延迟(ms)': f"{result.get('latency', 0):.2f}",
                        '下载速度(MB/s)': f"{result.get('download_speed', 0):.2f}",
                        '端口': result.get('port', 443),
                        '测速类型': result.get('test_type', '完全测速')
                    })
            
            self.log(f"结果已导出到: {filepath}")
            return filepath
        except Exception as e:
            self.log(f"导出失败: {str(e)}")
            return None
    
    async def run_ipv4_scan(self, port=443):
        """执行 IPv4 扫描"""
        self.log(f"开始 IPv4 扫描 (端口: {port})...")
        
        scanner = IPv4Scanner(
            log_callback=self.log,
            port=port
        )
        
        results = await scanner.run_scan_async()
        
        if results:
            self.log(f"IPv4 扫描完成，找到 {len(results)} 个可用 IP")
        else:
            self.log("IPv4 扫描未找到可用 IP")
        
        return results
    
    async def run_ipv6_scan(self, port=443):
        """执行 IPv6 扫描"""
        self.log(f"开始 IPv6 扫描 (端口: {port})...")
        
        scanner = IPv6Scanner(
            log_callback=self.log,
            port=port
        )
        
        results = await scanner.run_scan_async()
        
        if results:
            self.log(f"IPv6 扫描完成，找到 {len(results)} 个可用 IP")
        else:
            self.log("IPv6 扫描未找到可用 IP")
        
        return results
    
    def run_speed_test(self, results, test_type="完全测速", max_test_count=10, port=443):
        """执行测速"""
        if not results:
            self.log("没有扫描结果可测速")
            return []
        
        self.log(f"开始 {test_type} (端口: {port})...")
        
        speed_test_worker = SpeedTestWorker(
            results,
            max_test_count=max_test_count,
            current_port=port
        )
        
        # 连接信号
        speed_test_worker.status_message.connect(self.log)
        
        # 存储结果
        speed_results = []
        
        def on_completed(results):
            nonlocal speed_results
            speed_results = results
        
        speed_test_worker.speed_test_completed.connect(on_completed)
        
        # 开始测速
        speed_test_worker.start()
        speed_test_worker.wait()
        
        if speed_results:
            self.log(f"{test_type} 完成，成功测速 {len(speed_results)} 个 IP")
        else:
            self.log(f"{test_type} 未获取到测速结果")
        
        return speed_results
    
    async def run_full_scan(self):
        """执行完整扫描流程"""
        port = 443
        max_test_count = 10
        
        # 执行 IPv4 扫描
        ipv4_results = await self.run_ipv4_scan(port)
        if ipv4_results:
            ipv4_speed_results = self.run_speed_test(
                ipv4_results, "IPv4 完全测速", max_test_count, port
            )
            self.export_csv(ipv4_speed_results, "ipv4.csv")
        
        # 执行 IPv6 扫描
        ipv6_results = await self.run_ipv6_scan(port)
        if ipv6_results:
            ipv6_speed_results = self.run_speed_test(
                ipv6_results, "IPv6 完全测速", max_test_count, port
            )
            self.export_csv(ipv6_speed_results, "ipv6.csv")
        
        self.log("完整扫描流程完成")

def main():
    """主函数"""
    cli = CLI()
    
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(cli.run_full_scan())
    finally:
        loop.close()

if __name__ == "__main__":
    main()
