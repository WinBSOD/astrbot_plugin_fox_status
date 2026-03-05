import datetime
import platform
import psutil
import logging

# 获取 AstrBot 的系统日志实例
logger = logging.getLogger("astrbot")

def get_cpu_name():
    if platform.system() == "Windows":
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
            processor_name = winreg.QueryValueEx(key, "ProcessorNameString")[0]
            winreg.CloseKey(key)
            return processor_name.strip()
        except:
            pass
    elif platform.system() == "Linux":
        try:
            with open("/proc/cpuinfo", "r") as f:
                for line in f:
                    if "model name" in line:
                        return line.split(":")[1].strip()
        except:
            pass
    return platform.processor()

#获取系统详情
def get_system_info():
    try:
        return (
            f"  🖥️ 系统: {platform.system()} {platform.release()} {platform.machine()}\n"
        )
    except Exception:
        return "  🖥️ 系统: 获取失败\n"

#获取CPU温度
def get_cpu_temp():
    try:
        #Windows不可用
        func = getattr(psutil, "sensors_temperatures", None)
        if not func:
            return None
        temps = func()
        if not temps:
            return None
        # 增加对常见移动端/嵌入式设备温度节点的检测
        for name in ['coretemp', 'cpu_thermal', 'k10temp', 'zenpower', 'soc_thermal']:
            if name in temps and temps[name]:
                for entry in temps[name]:
                    if hasattr(entry, 'label') and 'Package' in entry.label: 
                        return entry.current
                return temps[name][0].current
        return None
    except:
        return None

#获取启动时间
def get_start_time_info():
    try:
        boot_time_timestamp = psutil.boot_time()
        bt = datetime.datetime.fromtimestamp(boot_time_timestamp)
        now = datetime.datetime.now()
        uptime = now - bt
        days = uptime.days
        hours, remainder = divmod(uptime.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        uptime_str = f"{days}天" if days > 0 else ""
        uptime_str += f"{hours}小时{minutes}分"
        
        return(
            f"  ⏱️ 启动时间: {bt.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"  ⌛ 已运行: {uptime_str}\n"
        )
    except Exception as e:
        logger.debug(f"获取启动时间失败: {e}")
        return "  ⌛ 已运行: 获取失败\n"

#获取CPU使用率
def get_cpu_info():
    try:
        temp = get_cpu_temp()
        temp_str = f" | 🌡️ {temp}°C" if temp is not None else ""
        # 容错处理：如果获取不到物理核心，就只显示逻辑核心
        p_count = psutil.cpu_count(logical=False)
        l_count = psutil.cpu_count(logical=True)
        core_str = f"{p_count}C/{l_count}T" if p_count else f"{l_count}T"
        # 缩短 interval 以提高响应速度
        percent = psutil.cpu_percent(interval=0.5)
        return(
            f"  🧠 CPU: {get_cpu_name()} ({core_str})\n"
            f"  📊 使用: {percent}%{temp_str}\n"
        )
    except Exception as e:
        logger.error(f"获取CPU详情失败: {e}")
        return "  🧠 CPU: 获取受限\n"

def bytes_to_gb(bytes_value):
    return round(bytes_value / (1024 ** 3), 2)

#获取内存使用详情
def get_mem_info():
    try:
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        info = f"  🐏 内存使用: {bytes_to_gb(mem.used)}/{bytes_to_gb(mem.total)} GB ({mem.percent}%)\n"
        # 只有当系统启用了 Swap 时才显示（防止某些环境没有 Swap 导致输出 0/0）
        if swap.total > 0:
            info += f"  🔄 交换分区: {bytes_to_gb(swap.used)}/{bytes_to_gb(swap.total)} GB ({swap.percent}%)\n"
        return info
    except Exception as e:
        logger.error(f"获取内存失败: {e}")
        return "  🐏 内存: 获取受限\n"
    
    
#获取硬盘信息
def get_disk_info(config):
    config = config or {}
    # 开关控制
    if not config.get("enable_disk", True):
        return ""
    
    disk_info = ""
    seen_disks = set()  # 用于去重功能
    try:
        partitions = psutil.disk_partitions()
        for partition in partitions:
            # 排除虚拟挂载点，减少报错几率
            if any(x in partition.mountpoint for x in ['/proc', '/sys', '/dev', '/var/lib/docker']):
                continue
            # 如果该挂载点已经处理过，直接跳过
            if partition.mountpoint in seen_disks:
                continue
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                # 针对 Android 的镜像挂载进一步去重：
                disk_id = (usage.total, usage.used)
                if disk_id in seen_disks:
                    continue
                disk_info += f"  💿 {partition.device} [{partition.fstype}] {bytes_to_gb(usage.used)}/{bytes_to_gb(usage.total)} GB ({usage.percent}%)\n"
                seen_disks.add(partition.mountpoint) # 记录路径
                seen_disks.add(disk_id)              # 记录 (total, used) 组合
            except (PermissionError, FileNotFoundError, OSError) as e:
                # 遇到报错直接跳过该分区，并打印调试日志
                logger.debug(f"跳过无法访问的磁盘分区 {partition.mountpoint}: {e}")
                continue
    except Exception as e:
        logger.warning(f"磁盘分区表读取失败: {e}")
    return disk_info

# 获取网络流量信息
def get_network_info(config):
    config = config or {}
    # 开关控制
    if not config.get("enable_net", True):
        return ""
        
    try:
        # psutil.net_io_counters() 在 Linux 下会读取 /proc/net/dev
        net_io = psutil.net_io_counters()
        sent = bytes_to_gb(net_io.bytes_sent)
        recv = bytes_to_gb(net_io.bytes_recv)
        return f"  🌐 流量: ⬆️ {sent} GB | ⬇️ {recv} GB\n"
        
    except (PermissionError, OSError) as e:
        # 针对 Android SELinux 拒绝访问 /proc/net/dev 的防御性处理
        logger.warning(f"网络信息读取受阻 (Android/容器限制): {e}")
        return "  🌐 网络: 权限受限，无法读取流量统计\n"
    except Exception:
        return ""

def get_all_info(config):
    config = config or {}
    
    all_info = "✨ 系统概览 ✨\n"
    all_info += get_system_info() 
    all_info += get_start_time_info()
    
    resource_body = "" # 用于判断下方标题是否显示的容器
    
    if config.get("enable_cpu", True):
        resource_body += get_cpu_info()
    if config.get("enable_mem", True):
        resource_body += get_mem_info()
    if config.get("enable_net", True):
        resource_body += get_network_info(config)
            
    # 只有当容器里有东西时，才整体贴上“📈 资源监控”的标题
    if resource_body.strip():
        all_info += "\n📈 资源监控\n" + resource_body

    if config.get("enable_disk", True):
        disk_text = get_disk_info(config)
        if disk_text.strip():
            all_info += "\n💾 存储空间\n" + disk_text
        
    return all_info.strip()