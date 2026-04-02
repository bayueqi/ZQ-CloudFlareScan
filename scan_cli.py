import sys
import random
import time
import ipaddress
import asyncio
import aiohttp
import socket
import ssl
from datetime import datetime
from typing import List, Optional, Dict
import csv
import os
import platform

# 默认IP段列表（作为API获取失败时的 fallback）
DEFAULT_IPV4_CIDRS = [

]

DEFAULT_IPV6_CIDRS = [

]

# 从CloudFlare API获取最新的IP段
def get_cloudflare_ips():
    """从CloudFlare API获取最新的IP段"""
    import requests
    import json
    
    url = "https://api.cloudflare.com/client/v4/ips"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                ipv4_cidrs = data["result"].get("ipv4_cidrs", [])
                ipv6_cidrs = data["result"].get("ipv6_cidrs", [])
                # 检查返回的数据是否为空
                if ipv4_cidrs or ipv6_cidrs:
                    print(f"成功从API获取IP段: IPv4({len(ipv4_cidrs)}), IPv6({len(ipv6_cidrs)})")
                    return ipv4_cidrs, ipv6_cidrs
                else:
                    print("API返回空数据，使用默认IP段")
    except Exception as e:
        print(f"获取CloudFlare IP段失败: {e}")
    
    # 如果API获取失败或返回空数据，使用默认IP段
    print("使用默认IP段")
    return DEFAULT_IPV4_CIDRS, DEFAULT_IPV6_CIDRS

# 初始化IP段
CF_IPV4_CIDRS, CF_IPV6_CIDRS = get_cloudflare_ips()

# 默认IATA码映射（作为API获取失败时的 fallback）
DEFAULT_AIRPORT_CODES = {

}

# 从URL获取IATA码映射
def get_airport_codes():
    """从URL获取IATA码映射"""
    import requests
    import json
    
    url = "https://cdn.jsdelivr.net/gh/LufsX/Cloudflare-Data-Center-IATA-Code-list/cloudflare-iata-zh.json"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            # 检查返回的数据是否为空
            if data:
                print(f"成功从API获取IATA码: {len(data)} 个")
                return data
            else:
                print("API返回空数据，使用默认IATA码")
    except Exception as e:
        print(f"获取IATA码失败: {e}")
    
    # 如果API获取失败或返回空数据，使用默认IATA码
    print("使用默认IATA码")
    return DEFAULT_AIRPORT_CODES

# 初始化IATA码
AIRPORT_CODES = get_airport_codes()

PORT_OPTIONS = ["443", "2053", "2083", "2087", "2096", "8443"]

def get_iata_code_from_ip(ip: str, timeout: int = 3) -> Optional[str]:
    test_host = "speed.cloudflare.com"
    
    if ':' in ip:
        urls = [
            f"https://[{ip}]/cdn-cgi/trace",
            f"http://[{ip}]/cdn-cgi/trace",
        ]
    else:
        urls = [
            f"https://{ip}/cdn-cgi/trace",
            f"http://{ip}/cdn-cgi/trace",
        ]
    
    for url in urls:
        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            
            if url.startswith('https://'):
                use_ssl = True
                if '[' in url and ']' in url:
                    host = url[8:].split('/')[0].strip('[]')
                else:
                    host = url[8:].split('/')[0]
            else:
                use_ssl = False
                if '[' in url and ']' in url:
                    host = url[7:].split('/')[0].strip('[]')
                else:
                    host = url[7:].split('/')[0]
            
            port = 443 if use_ssl else 80
            
            if ':' in host:
                addrinfo = socket.getaddrinfo(host, port, socket.AF_INET6, socket.SOCK_STREAM)
                family, socktype, proto, canonname, sockaddr = addrinfo[0]
                s = socket.socket(family, socktype, proto)
                s.settimeout(timeout)
                s.connect(sockaddr)
            else:
                s = socket.create_connection((host, port), timeout=timeout)
            
            if use_ssl:
                s = ctx.wrap_socket(s, server_hostname=test_host)
            
            request = f"GET /cdn-cgi/trace HTTP/1.1\r\nHost: {test_host}\r\nUser-Agent: Mozilla/5.0\r\nConnection: close\r\n\r\n".encode()
            s.sendall(request)
            
            data = b""
            while True:
                try:
                    chunk = s.recv(4096)
                    if not chunk:
                        break
                    data += chunk
                    if b"\r\n\r\n" in data:
                        header_end = data.find(b"\r\n\r\n")
                        body = data[header_end + 4:]
                        break
                except socket.timeout:
                    break
            
            s.close()
            
            response_text = body.decode('utf-8', errors='ignore')
            for line in response_text.splitlines():
                if line.startswith('colo='):
                    colo_value = line.split('=', 1)[1].strip()
                    if colo_value and colo_value.upper() != 'UNKNOWN':
                        return colo_value.upper()
            
            if b'CF-RAY' in data:
                for line in data.decode('utf-8', errors='ignore').split('\r\n'):
                    if line.startswith('CF-RAY:'):
                        cf_ray = line.split(':', 1)[1].strip()
                        if '-' in cf_ray:
                            parts = cf_ray.split('-')
                            for part in parts[-2:]:
                                if len(part) == 3 and part.isalpha():
                                    return part.upper()
            
        except Exception:
            continue
    
    return None

async def get_iata_code_async(session: aiohttp.ClientSession, ip: str, timeout: int = 3) -> Optional[str]:
    test_host = "speed.cloudflare.com"
    
    if ':' in ip:
        urls = [
            f"https://[{ip}]/cdn-cgi/trace",
            f"http://[{ip}]/cdn-cgi/trace",
        ]
    else:
        urls = [
            f"https://{ip}/cdn-cgi/trace",
            f"http://{ip}/cdn-cgi/trace",
        ]
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Host": test_host
    }
    
    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE
    
    for url in urls:
        try:
            use_ssl = url.startswith('https://')
            ssl_context = ssl_ctx if use_ssl else None
            
            async with session.get(
                url,
                headers=headers,
                ssl=ssl_context,
                timeout=aiohttp.ClientTimeout(total=timeout),
                allow_redirects=False
            ) as response:
                if response.status == 200:
                    text = await response.text()
                    
                    for line in text.strip().split('\n'):
                        if line.startswith('colo='):
                            colo_value = line.split('=', 1)[1].strip()
                            if colo_value and colo_value.upper() != 'UNKNOWN':
                                return colo_value.upper()
                    
                    if 'CF-RAY' in response.headers:
                        cf_ray = response.headers['CF-RAY']
                        if '-' in cf_ray:
                            parts = cf_ray.split('-')
                            for part in parts[-2:]:
                                if len(part) == 3 and part.isalpha():
                                    return part.upper()
                
        except Exception:
            continue
    
    return None

def get_iata_translation(iata_code: str) -> str:
    if iata_code in AIRPORT_CODES:
        return AIRPORT_CODES[iata_code]
    return iata_code

async def async_tcp_ping(ip: str, port: int, timeout: float = 1.0) -> Optional[float]:
    start_time = time.monotonic()
    
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(ip, port),
            timeout=timeout
        )
        latency = (time.monotonic() - start_time) * 1000
        writer.close()
        await writer.wait_closed()
        return round(latency, 2)
    
    except (asyncio.TimeoutError, ConnectionRefusedError, OSError, ConnectionError):
        return None
    except Exception:
        return None

async def measure_tcp_latency(ip: str, port: int, ping_times: int = 4, timeout: float = 1.0) -> Optional[float]:
    latencies = []
    
    for i in range(ping_times):
        latency = await async_tcp_ping(ip, port, timeout)
        if latency is not None:
            latencies.append(latency)
        
        if i < ping_times - 1:
            await asyncio.sleep(0.05)
    
    if latencies:
        return min(latencies)
    else:
        return None

class IPv4Scanner:
    def __init__(self, log_callback=None, progress_callback=None, port=443):
        self.max_workers = 200
        self.timeout = 1.0
        self.ping_times = 3
        self.running = True
        self.log_callback = log_callback
        self.progress_callback = progress_callback
        self.port = port
        
    def generate_ips_from_cidrs(self) -> List[str]:
        ip_list = []
        for cidr in CF_IPV4_CIDRS:
            try:
                network = ipaddress.ip_network(cidr, strict=False)
                
                for subnet in network.subnets(new_prefix=24):
                    if subnet.num_addresses > 2:
                        hosts = list(subnet.hosts())
                        if hosts:
                            selected_ips = random.sample(hosts, 2)
                            for ip in selected_ips:
                                ip_list.append(str(ip))
                            
            except ValueError as e:
                if self.log_callback:
                    self.log_callback(f"处理CIDR {cidr} 时出错: {e}")
                continue
        
        return ip_list
    
    async def test_ip_latency(self, session: aiohttp.ClientSession, ip: str) -> Optional[float]:
        if not self.running:
            return None
            
        return await measure_tcp_latency(ip, self.port, self.ping_times, self.timeout)
    
    async def test_single_ip(self, session: aiohttp.ClientSession, ip: str):
        if not self.running:
            return None
        
        latency = await self.test_ip_latency(session, ip)
        
        if latency is not None and latency < 230:
            iata_code = None
            if self.running:
                try:
                    iata_code = await get_iata_code_async(session, ip, self.timeout)
                except Exception as e:
                    if self.log_callback:
                        self.log_callback(f"获取地区码失败 {ip}: {str(e)}")
                    iata_code = None
                    
            return {
                'ip': ip,
                'latency': latency,
                'iata_code': iata_code,
                'chinese_name': get_iata_translation(iata_code) if iata_code else "未知地区",
                'success': True,
                'ip_version': 4,
                'scan_time': datetime.now().strftime("%H:%M:%S"),
                'port': self.port,
                'ping_times': self.ping_times
            }
        else:
            return None
    
    async def batch_test_ips(self, ip_list: List[str]):
        semaphore = asyncio.Semaphore(self.max_workers)
        
        async def test_with_semaphore(session: aiohttp.ClientSession, ip: str):
            async with semaphore:
                return await self.test_single_ip(session, ip)
        
        connector = aiohttp.TCPConnector(
            limit=self.max_workers,
            force_close=True,
            enable_cleanup_closed=True,
            limit_per_host=0
        )
        
        successful_results = []
        start_time = time.time()
        
        async with aiohttp.ClientSession(connector=connector) as session:
            tasks = []
            for ip in ip_list:
                if not self.running:
                    break
                task = asyncio.create_task(test_with_semaphore(session, ip))
                tasks.append(task)
            
            completed = 0
            total = len(tasks)
            
            last_update_time = time.time()
            update_interval = 0.5
            
            for future in asyncio.as_completed(tasks):
                if not self.running:
                    for task in tasks:
                        if not task.done():
                            task.cancel()
                    break
                
                result = await future
                completed += 1
                
                if result:
                    successful_results.append(result)
                
                current_time = time.time()
                if current_time - last_update_time >= update_interval or completed == total:
                    elapsed = current_time - start_time
                    ips_per_second = completed / elapsed if elapsed > 0 else 0
                    
                    if self.progress_callback:
                        self.progress_callback(completed, total, len(successful_results), ips_per_second)
                    
                    last_update_time = current_time
        
        return successful_results
    
    async def run_scan_async(self):
        try:
            if self.log_callback:
                self.log_callback(f"正在从Cloudflare IPv4 IP段生成随机IP... (端口: {self.port})")
            ip_list = self.generate_ips_from_cidrs()
            
            if not ip_list:
                if self.log_callback:
                    self.log_callback("错误: 未能生成IPv4 IP列表")
                return None
            
            if self.log_callback:
                self.log_callback(f"已生成 {len(ip_list)} 个随机IPv4 IP")
                self.log_callback(f"开始延迟测试 {len(ip_list)} 个IPv4 IP...")
            
            results = await self.batch_test_ips(ip_list)
            
            if not self.running:
                if self.log_callback:
                    self.log_callback("IPv4扫描被用户中止")
                return None
            
            return results
            
        except Exception as e:
            if self.log_callback:
                self.log_callback(f"IPv4扫描过程中出现错误: {str(e)}")
            return None
    
    def stop(self):
        self.running = False

class IPv6Scanner:
    def __init__(self, log_callback=None, progress_callback=None, port=443):
        self.max_workers = 200
        self.timeout = 1.0
        self.ping_times = 2
        self.running = True
        self.log_callback = log_callback
        self.progress_callback = progress_callback
        self.port = port
        
    def generate_ips_from_cidrs(self) -> List[str]:
        ip_list = []
        
        for cidr in CF_IPV6_CIDRS:
            try:
                network = ipaddress.ip_network(cidr, strict=False)
                
                if network.num_addresses > 2:
                    sample_size = min(200, network.num_addresses - 2)
                    try:
                        for _ in range(sample_size):
                            random_ip_int = random.randint(int(network.network_address) + 1, 
                                                           int(network.broadcast_address) - 1)
                            random_ip = str(ipaddress.IPv6Address(random_ip_int))
                            ip_list.append(random_ip)
                    except ValueError as e:
                        if self.log_callback:
                            self.log_callback(f"处理IPv6 CIDR {cidr} 时出错: {e}")
                        continue
                            
            except ValueError as e:
                if self.log_callback:
                    self.log_callback(f"处理CIDR {cidr} 时出错: {e}")
                continue
        
        return ip_list
    
    async def test_ip_latency(self, session: aiohttp.ClientSession, ip: str) -> Optional[float]:
        if not self.running:
            return None
            
        return await measure_tcp_latency(ip, self.port, self.ping_times, self.timeout)
    
    async def test_single_ip(self, session: aiohttp.ClientSession, ip: str):
        if not self.running:
            return None
        
        latency = await self.test_ip_latency(session, ip)
        
        if latency is not None and latency < 320:
            iata_code = None
            if self.running:
                try:
                    iata_code = await get_iata_code_async(session, ip, self.timeout)
                except Exception as e:
                    if self.log_callback:
                        self.log_callback(f"获取地区码失败 {ip}: {str(e)}")
                    pass
            
            return {
                'ip': ip,
                'latency': latency,
                'iata_code': iata_code,
                'chinese_name': get_iata_translation(iata_code) if iata_code else "未知地区",
                'success': True,
                'ip_version': 6,
                'scan_time': datetime.now().strftime("%H:%M:%S"),
                'port': self.port,
                'ping_times': self.ping_times
            }
        else:
            return None
    
    async def batch_test_ips(self, ip_list: List[str]):
        semaphore = asyncio.Semaphore(self.max_workers)
        
        async def test_with_semaphore(session: aiohttp.ClientSession, ip: str):
            async with semaphore:
                return await self.test_single_ip(session, ip)
        
        connector = aiohttp.TCPConnector(
            limit=self.max_workers,
            force_close=True,
            enable_cleanup_closed=True,
            limit_per_host=0,
            family=socket.AF_INET6
        )
        
        successful_results = []
        start_time = time.time()
        
        async with aiohttp.ClientSession(connector=connector) as session:
            tasks = []
            for ip in ip_list:
                if not self.running:
                    break
                task = asyncio.create_task(test_with_semaphore(session, ip))
                tasks.append(task)
            
            completed = 0
            total = len(tasks)
            
            last_update_time = time.time()
            update_interval = 0.5
            
            for future in asyncio.as_completed(tasks):
                if not self.running:
                    for task in tasks:
                        if not task.done():
                            task.cancel()
                    break
                
                try:
                    result = await future
                    completed += 1
                    
                    if result:
                        successful_results.append(result)
                    
                    current_time = time.time()
                    if current_time - last_update_time >= update_interval or completed == total:
                        elapsed = current_time - start_time
                        ips_per_second = completed / elapsed if elapsed > 0 else 0
                        
                        if self.progress_callback:
                            self.progress_callback(completed, total, len(successful_results), ips_per_second)
                        
                        last_update_time = current_time
                except Exception:
                    completed += 1
        
        return successful_results
    
    async def run_scan_async(self):
        try:
            if self.log_callback:
                self.log_callback(f"正在从Cloudflare IPv6 IP段生成随机IP... (端口: {self.port})")
            ip_list = self.generate_ips_from_cidrs()
            
            if not ip_list:
                if self.log_callback:
                    self.log_callback("错误: 未能生成IPv6 IP列表")
                return None
            
            if self.log_callback:
                self.log_callback(f"已生成 {len(ip_list)} 个随机IPv6 IP")
                self.log_callback(f"开始延迟测试 {len(ip_list)} 个IPv6 IP...")
                self.log_callback("注意: IPv6扫描可能需要更多时间，请耐心等待...")
            
            results = await self.batch_test_ips(ip_list)
            
            if not self.running:
                if self.log_callback:
                    self.log_callback("IPv6扫描被用户中止")
                return None
            
            if results:
                with_iata = sum(1 for r in results if r.get('iata_code'))
                if self.log_callback:
                    self.log_callback(f"IPv6扫描完成: 共{len(results)}个IP可用，其中{with_iata}个成功获取地区码")
            
            return results
            
        except Exception as e:
            if self.log_callback:
                self.log_callback(f"IPv6扫描过程中出现错误: {str(e)}")
            return None
    
    def stop(self):
        self.running = False

def download_speed(ip: str, port: int) -> float:
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    test_host = "speed.vpnjacky.dpdns.org"
    
    req = (
        "GET /50M HTTP/1.1\r\n"
        f"Host: {test_host}\r\n"
        "User-Agent: Mozilla/5.0\r\n"
        "Accept: */*\r\n"
        "Connection: close\r\n\r\n"
    ).encode()

    try:
        if ':' in ip:
            addrinfo = socket.getaddrinfo(ip, port, socket.AF_INET6, socket.SOCK_STREAM)
            family, socktype, proto, canonname, sockaddr = addrinfo[0]
            sock = socket.socket(family, socktype, proto)
            sock.settimeout(3)
            sock.connect(sockaddr)
        else:
            sock = socket.create_connection((ip, port), timeout=3)
            
        ss = ctx.wrap_socket(sock, server_hostname=test_host)
        ss.sendall(req)

        start = time.time()
        data = b""
        header_done = False
        body = 0
        download_time_limit = 3

        while time.time() - start < download_time_limit:
            buf = ss.recv(8192)
            if not buf:
                break
            if not header_done:
                data += buf
                if b"\r\n\r\n" in data:
                    header_done = True
                    body += len(data.split(b"\r\n\r\n", 1)[1])
            else:
                body += len(buf)

        ss.close()
        dur = time.time() - start
        return round((body / 1024 / 1024) / max(dur, 0.1), 2)

    except Exception as e:
        print(f"测速失败 {ip}: {str(e)}")
        return 0.0

def run_speed_test(results: List[Dict], max_test_count=10, port=443) -> List[Dict]:
    if not results:
        print("错误：没有可用的IP进行测速")
        return []
    
    results.sort(key=lambda x: x.get('latency', float('inf')))
    target_ips = results[:min(max_test_count, len(results))]
    
    print(f"开始测速：将对 {len(target_ips)} 个IP进行测速 (端口: {port})")
    
    speed_results = []
    
    for i, ip_info in enumerate(target_ips):
        ip = ip_info['ip']
        latency = ip_info.get('latency', 0)
        
        print(f"[{i+1}/{len(target_ips)}] 正在测速 {ip} (端口: {port})")
        
        download_speed_val = download_speed(ip, port)
        
        colo = get_iata_code_from_ip(ip, timeout=3)
        if not colo or colo == "Unknown":
            colo = ip_info.get('iata_code', 'UNKNOWN')
        
        speed_result = {
            'ip': ip,
            'latency': latency,
            'download_speed': download_speed_val,
            'iata_code': colo.upper() if colo else 'UNKNOWN',
            'chinese_name': AIRPORT_CODES.get(colo.upper(), '未知地区') if colo else '未知地区',
            'test_type': '完全测速',
            'port': port  
        }
        
        speed_results.append(speed_result)
        
        print(f"  测速结果: {download_speed_val} MB/s, 地区: {speed_result['chinese_name']}")
        
        if i < len(target_ips) - 1:
            time.sleep(3)
    
    speed_results.sort(key=lambda x: x['download_speed'], reverse=True)
    
    if speed_results:
        print(f"测速完成！成功测速 {len(speed_results)}/{len(target_ips)} 个IP")
    else:
        print(f"所有IP测速失败")
    
    return speed_results

def save_results_to_csv(results: List[Dict], filename: str):
    if not results:
        print(f"警告：没有结果可保存到 {filename}")
        return
    
    with open(filename, 'w', newline='', encoding='utf-8-sig') as csvfile:
        fieldnames = ['排名', 'IP地址', '地区码', '地区', '延迟(ms)', '下载速度(MB/s)', '端口', '测速类型']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        
        for i, result in enumerate(results, 1):
            writer.writerow({
                '排名': i,
                'IP地址': result['ip'],
                '地区码': result['iata_code'],
                '地区': result['chinese_name'],
                '延迟(ms)': f"{result['latency']:.2f}",
                '下载速度(MB/s)': f"{result['download_speed']:.2f}",
                '端口': result.get('port', 443),
                '测速类型': result.get('test_type', '未知')
            })
    
    print(f"结果已保存到: {filename}")

def log_callback(msg):
    print(msg)

def progress_callback(current, total, success_count, speed):
    print(f"扫描进度: {current}/{total} ({success_count}个可用) - {speed:.1f} IP/秒")

async def main():
    port = 443
    iata_code = os.environ.get('IATA_CODE', '').strip().upper()
    
    if iata_code:
        print(f"指定 IATA 码: {iata_code}，将只保留该地区的结果")
    
    # IPv4 扫描
    print("=" * 50)
    print("开始 IPv4 扫描")
    print("=" * 50)
    ipv4_scanner = IPv4Scanner(
        log_callback=log_callback,
        progress_callback=progress_callback,
        port=port
    )
    ipv4_results = await ipv4_scanner.run_scan_async()
    
    if ipv4_results:
        print(f"\nIPv4 扫描完成，共找到 {len(ipv4_results)} 个可用IP")
        
        # 如果指定了 IATA 码，只保留该地区的
        if iata_code:
            ipv4_results = [r for r in ipv4_results if r.get('iata_code') == iata_code]
            print(f"已过滤为 {iata_code} 地区的 {len(ipv4_results)} 个IP")
        
        if ipv4_results:
            print("开始 IPv4 测速...")
            ipv4_speed_results = run_speed_test(ipv4_results, max_test_count=20, port=port)
            save_results_to_csv(ipv4_speed_results, "ipv4.csv")
        else:
            print("过滤后没有可用IP")
    else:
        print("IPv4 扫描未找到可用IP")
    
    # IPv6 扫描
    print("\n" + "=" * 50)
    print("开始 IPv6 扫描")
    print("=" * 50)
    ipv6_scanner = IPv6Scanner(
        log_callback=log_callback,
        progress_callback=progress_callback,
        port=port
    )
    ipv6_results = await ipv6_scanner.run_scan_async()
    
    if ipv6_results:
        print(f"\nIPv6 扫描完成，共找到 {len(ipv6_results)} 个可用IP")
        
        # 如果指定了 IATA 码，只保留该地区的
        if iata_code:
            ipv6_results = [r for r in ipv6_results if r.get('iata_code') == iata_code]
            print(f"已过滤为 {iata_code} 地区的 {len(ipv6_results)} 个IP")
        
        if ipv6_results:
            print("开始 IPv6 测速...")
            ipv6_speed_results = run_speed_test(ipv6_results, max_test_count=20, port=port)
            save_results_to_csv(ipv6_speed_results, "ipv6.csv")
        else:
            print("过滤后没有可用IP")
    else:
        print("IPv6 扫描未找到可用IP")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    asyncio.run(main())
