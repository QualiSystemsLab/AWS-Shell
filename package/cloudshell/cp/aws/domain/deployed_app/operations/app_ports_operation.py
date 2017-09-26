from cloudshell.shell.core.driver_context import ResourceContextDetails
from jsonpickle import json

from cloudshell.cp.aws.domain.services.parsers.port_group_attribute_parser import PortGroupAttributeParser
from cloudshell.cp.aws.models.port_data import PortData
from cloudshell.cp.aws.domain.services.parsers.custom_param_extractor import VmCustomParamsExtractor


class DeployedAppPortsOperation(object):
    def __init__(self, vm_custom_params_extractor, security_group_service, instance_service):
        """
        :param VmCustomParamsExtractor vm_custom_params_extractor:
        :param security_group_service:
        :type security_group_service: cloudshell.cp.aws.domain.services.ec2.security_group.SecurityGroupService
        :return:
        """
        self.vm_custom_params_extractor = vm_custom_params_extractor
        self.security_group_service = security_group_service
        self.instance_service = instance_service

    def get_formated_deployed_app_ports(self, custom_params):
        """
        :param custom_params:
        :return:
        """
        inbound_ports_value = self.vm_custom_params_extractor.get_custom_param_value(custom_params, "inbound_ports")
        outbound_ports_value = self.vm_custom_params_extractor.get_custom_param_value(custom_params, "outbound_ports")

        if not inbound_ports_value and not outbound_ports_value:
            return "No ports are open for inbound and outbound traffic outside of the Sandbox"

        result_str_list = []

        if inbound_ports_value:
            inbound_ports = PortGroupAttributeParser.parse_port_group_attribute(inbound_ports_value)
            if inbound_ports:
                result_str_list.append("Inbound ports:")
                for rule in inbound_ports:
                    result_str_list.append(self._port_rule_to_string(rule))
                result_str_list.append('')

        if outbound_ports_value:
            outbound_ports = PortGroupAttributeParser.parse_port_group_attribute(outbound_ports_value)
            if outbound_ports:
                result_str_list.append("Outbound ports:")
                for rule in outbound_ports:
                    result_str_list.append(self._port_rule_to_string(rule))

        return '\n'.join(result_str_list).strip()

    def get_app_ports_from_cloud_provider(self, ec2_session, instance_id, resource):
        """
        :param ec2_session: EC2 session
        :param string instance_id:
        :param ResourceContextDetails resource:
        """
        instance = self.instance_service.get_active_instance_by_id(ec2_session, instance_id)
        network_interfaces = instance.network_interfaces

        result_str_list = ['App Name: ' + resource.fullname]

        # todo "Allow Sandbox traffic" attribute is [True/False] - when define app as isolated will be finished

        for network_interface in network_interfaces:
            subnet_id = network_interface.subnet_id
            result_str_list.append('Subnet Name: ' + subnet_id)

            custom_security_group = self.security_group_service.get_custom_security_group(
                ec2_session=ec2_session,
                network_interface=network_interface)

            inbound_ports_security_group = self.security_group_service.get_inbound_ports_security_group(
                ec2_session=ec2_session,
                network_interface=network_interface)

            security_groups = []
            if custom_security_group:
                security_groups.append(custom_security_group)
            if inbound_ports_security_group:
                security_groups.append(inbound_ports_security_group)

            for security_group in security_groups:
                ip_permissions = security_group.ip_permissions
                ip_permissions_string = self._ip_permissions_to_string(ip_permissions)
                if ip_permissions_string:
                    result_str_list.append(ip_permissions_string)

        return '\n'.join(result_str_list).strip()

    def _ip_permissions_to_string(self, ip_permissions):
        if not isinstance(ip_permissions, list):
            return None

        result = []

        for ip_permission in ip_permissions:
            if ip_permission['FromPort'] == ip_permission['ToPort']:
                port_str = ip_permission['FromPort']
                port_postfix = ""
            else:
                port_str = "{0}-{1}".format(ip_permission['FromPort'], ip_permission['ToPort'])
                port_postfix = "s"

            result.append("Port{0}: {1}, Protocol: {2}, \nSource: {3}".format(port_postfix, port_str,
                                                                              ip_permission['IpProtocol'],
                                                                              self._convert_ip_ranges_to_string(ip_permission['IpRanges'])))
        return '\n'.join(result).strip()

    def _convert_ip_ranges_to_string(self, ip_ranges):
        if not isinstance(ip_ranges, list):
            return None

        result = ''

        for ip_range in ip_ranges:
            if not isinstance(ip_range, dict):
                continue
            cidr = ip_range.get('CidrIp')
            if cidr:
                result = result.join('{}'.format(cidr))

        return result

    def _port_rule_to_string(self, port_rule):
        """
        :param PortData port_rule:
        :return:
        """
        if port_rule.from_port == port_rule.to_port:
            port_str = port_rule.from_port
            port_postfix = ""
        else:
            port_str = "{0}-{1}".format(port_rule.from_port, port_rule.to_port)
            port_postfix = "s"

        return "Port{0} {1} {2}".format(port_postfix, port_str, port_rule.protocol)
