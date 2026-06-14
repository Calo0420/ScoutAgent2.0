"""
VMware Scout Tools — covers A5 (VMware Cost Optimizer)
Connects to vCenter via pyVmomi. Read-only. No changes made.
"""
import ssl

from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim


def scan_vmware_environment(vcenter_host: str, username: str, password: str, port: int = 443) -> dict:
    """
    A5 — VMware Cost Optimizer: pulls VM inventory, finds rightsizing candidates,
    flags powered-off VMs wasting licensing, estimates savings.
    """
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode    = ssl.CERT_NONE

    si = SmartConnect(host=vcenter_host, user=username, pwd=password, port=port, sslContext=context)
    try:
        content   = si.RetrieveContent()
        container = content.viewManager.CreateContainerView(
            content.rootFolder, [vim.VirtualMachine], True
        )
        vms = container.view

        total_vms    = 0
        powered_off  = []
        oversized    = []
        snapshots    = []
        total_vcpu   = 0
        total_ram_gb = 0

        for vm in vms:
            total_vms += 1
            cfg   = vm.config
            stats = vm.summary.quickStats

            vcpu  = cfg.hardware.numCPU
            ram   = cfg.hardware.memoryMB / 1024
            total_vcpu   += vcpu
            total_ram_gb += ram

            if vm.runtime.powerState == "poweredOff":
                powered_off.append({"name": vm.name, "vcpu": vcpu, "ram_gb": round(ram, 1)})

            # Flag VMs with >4 vCPU and <10% CPU usage as oversized candidates
            if vcpu > 4 and stats.overallCpuUsage and stats.overallCpuUsage < (vcpu * 100 * 0.10):
                oversized.append({
                    "name":          vm.name,
                    "vcpu":          vcpu,
                    "cpu_usage_mhz": stats.overallCpuUsage,
                    "ram_gb":        round(ram, 1),
                    "suggestion":    f"Downsize to {vcpu // 2} vCPU",
                })

            if vm.snapshot:
                snapshots.append(vm.name)

        recoverable_licenses = len(powered_off) + len(oversized)
        return {
            "vcenter":                  vcenter_host,
            "total_vms":                total_vms,
            "total_vcpu":               total_vcpu,
            "total_ram_gb":             round(total_ram_gb, 1),
            "powered_off_vms":          powered_off,
            "oversized_vms":            oversized,
            "vms_with_snapshots":       snapshots,
            "recoverable_licenses":     recoverable_licenses,
            "estimated_savings_usd_yr": recoverable_licenses * 200,
        }
    finally:
        Disconnect(si)
