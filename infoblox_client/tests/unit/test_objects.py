# Copyright 2014 OpenStack LLC.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import copy
import mock

from infoblox_client import objects
from infoblox_client.tests import base

DEFAULT_HOST_RECORD = {
    '_ref': 'record:host/ZG5zLmhvc3QkLl9kZWZhdWx0LmNvbS5nbG9iYWwuY22NA'
            ':test_host_name.testsubnet.cloud.global.com/default',
    'ipv4addrs': [{
        'configure_for_dhcp': False,
        '_ref': 'record:host_ipv4addr/lMmQ3ZjkuM4Zj5Mi00Y2:22.0.0.2/'
                'test_host_name.testsubnet.cloud.global.com/default',
        'ipv4addr': '22.0.0.2',
        'mac': 'fa:16:3e:29:87:70',
        'host': '2c8f8e97-0d92-4cac-a350-096ff2b79.cloud.global.com'}],
    'extattrs': {
        'Account': {'value': '8a21c40495f04f30a1b2dc6fd1d9ed1a'},
        'Cloud API Owned': {'value': 'True'},
        'VM ID': {'value': 'None'},
        'IP Type': {'value': 'Fixed'},
        'CMP Type': {'value': 'OpenStack'},
        'Port ID': {'value': '136ef9ad-9c88-41ea-9fa6-bd48d8ec789a'},
        'Tenant ID': {'value': '00fd80791dee4112bb538c872b206d4c'}}
}


class TestObjects(base.TestCase):

    def _mock_connector(self, get_object=None, create_object=None,
                        delete_object=None):
        connector = mock.Mock()
        connector.get_object.return_value = get_object
        connector.create_object.return_value = create_object
        connector.delete_object.return_value = delete_object
        return connector

    def test_search_network(self):
        connector = self._mock_connector()

        objects.Network.search(connector,
                               network_view='some-view',
                               cidr='192.68.1.0/20')
        connector.get_object.assert_called_once_with(
            'network',
            {'network_view': 'some-view', 'network': '192.68.1.0/20'},
            extattrs=None, force_proxy=False, return_fields=mock.ANY)

    def test_search_network_v6(self):
        connector = self._mock_connector()

        objects.Network.search(connector,
                               network_view='some-view',
                               cidr='fffe:2312::/64')
        connector.get_object.assert_called_once_with(
            'ipv6network',
            {'network_view': 'some-view', 'network': 'fffe:2312::/64'},
            extattrs=None, force_proxy=False, return_fields=mock.ANY)

    def test_search_network_v6_using_network_field(self):
        connector = self._mock_connector()

        objects.Network.search(connector,
                               network_view='some-view',
                               network='fffe:2312::/64')
        connector.get_object.assert_called_once_with(
            'ipv6network',
            {'network_view': 'some-view', 'network': 'fffe:2312::/64'},
            extattrs=None, force_proxy=False, return_fields=mock.ANY)

    def test_search_network_with_results(self):
        found = {"_ref": "network/ZG5zLm5ldHdvcmskMTAuMzkuMTEuMC8yNC8w"
                         ":10.39.11.0/24/default",
                 "network_view": 'some-view',
                 "network": '192.68.1.0/20'}
        connector = self._mock_connector(get_object=[found])

        network = objects.Network.search(connector,
                                         network_view='some-view',
                                         cidr='192.68.1.0/20')
        connector.get_object.assert_called_once_with(
            'network',
            {'network_view': 'some-view', 'network': '192.68.1.0/20'},
            extattrs=None, force_proxy=False, return_fields=mock.ANY)
        self.assertEqual('192.68.1.0/20', network.network)
        self.assertEqual('some-view', network.network_view)
        # verify aliased fields works too
        self.assertEqual('192.68.1.0/20', network.cidr)

    def test_create_IP(self):
        ip = objects.IP.create(ip='192.168.1.12', mac='4a:ac:de:12:34:45')
        self.assertIsInstance(ip, objects.IPv4)
        self.assertEqual('192.168.1.12', ip.ip)
        self.assertEqual('192.168.1.12', ip.ipv4addr)
        self.assertEqual('4a:ac:de:12:34:45', ip.mac)
        self.assertEqual(None, ip.configure_for_dhcp)
        self.assertEqual(None, ip.host)

    def test_create_host_record_with_ip(self):
        mock_record = DEFAULT_HOST_RECORD
        host_record_copy = copy.deepcopy(mock_record)
        connector = self._mock_connector(create_object=host_record_copy)

        ip = objects.IP.create(ip='22.0.0.2', mac='fa:16:3e:29:87:70')
        self.assertIsInstance(ip, objects.IPv4)

        host_record = objects.HostRecord.create(connector,
                                                view='some-dns-view',
                                                ip=[ip])
        # Validate that ip object was converted to simple ip
        # as a string representation for searching
        connector.get_object.assert_called_once_with(
            'record:host',
            {'view': 'some-dns-view', 'ipv4addr': '22.0.0.2'},
            return_fields=mock.ANY)
        # Validate create_object call
        ip_dict = {'ipv4addr': '22.0.0.2', 'mac': 'fa:16:3e:29:87:70'}
        connector.create_object.assert_called_once_with(
            'record:host',
            {'view': 'some-dns-view', 'ipv4addrs': [ip_dict]}, mock.ANY)
        self.assertIsInstance(host_record, objects.HostRecordV4)
        # validate nios reply was parsed correctly
        self.assertEqual(mock_record['_ref'], host_record._ref)
        nios_ip = host_record.ipv4addrs[0]
        self.assertIsInstance(ip, objects.IPv4)
        self.assertEqual(mock_record['ipv4addrs'][0]['mac'], nios_ip.mac)
        self.assertEqual(mock_record['ipv4addrs'][0]['ipv4addr'],
                         nios_ip.ipv4addr)
        self.assertEqual(mock_record['ipv4addrs'][0]['host'],
                         nios_ip.host)
        self.assertEqual(mock_record['ipv4addrs'][0]['configure_for_dhcp'],
                         nios_ip.configure_for_dhcp)
        # Validate 'host' field is not send on update
        new_ip = objects.IP.create(ip='22.0.0.10', mac='fa:16:3e:29:87:71',
                                   configure_for_dhcp=False)
        host_record.ip.append(new_ip)
        host_record.extattrs = {}
        host_record.update()
        ip_dict['configure_for_dhcp'] = False
        ip_dict_new = {'ipv4addr': '22.0.0.10', 'mac': 'fa:16:3e:29:87:71',
                       'configure_for_dhcp': False}
        connector.update_object.assert_called_once_with(
            host_record.ref,
            {'ipv4addrs': [ip_dict, ip_dict_new],
             'extattrs': {}}, mock.ANY)

    def test_search_and_delete_host_record(self):
        host_record_copy = copy.deepcopy(DEFAULT_HOST_RECORD)
        connector = self._mock_connector(get_object=[host_record_copy])

        host_record = objects.HostRecord.search(connector,
                                                view='some-dns-view',
                                                ip='192.168.15.20')
        connector.get_object.assert_called_once_with(
            'record:host',
            {'view': 'some-dns-view', 'ipv4addr': '192.168.15.20'},
            extattrs=None, force_proxy=False, return_fields=mock.ANY)

        # Validate extattrs in host_record are converted to EA object
        self.assertIsInstance(host_record.extattrs, objects.EA)

        host_record.delete()
        connector.delete_object.assert_called_once_with(
            DEFAULT_HOST_RECORD['_ref'])

    def test_create_fixed_address(self):
        mock_fixed_address = {
            '_ref': 'fixedaddress/ZG5zLmhvc3QkLl9kZWZhdWx0LmNvbS5nbG9iYWw2NA',
            'ipv4addr': '192.168.1.15',
            'mac': 'aa:ac:cd:11:22:33',
        }
        connector = self._mock_connector(create_object=mock_fixed_address)

        fixed_addr = objects.FixedAddress.create(connector,
                                                 ip='192.168.1.15',
                                                 network_view='some-view',
                                                 mac='aa:ac:cd:11:22:33')
        connector.get_object.assert_called_once_with(
            'fixedaddress',
            {'network_view': 'some-view', 'ipv4addr': '192.168.1.15',
             'mac': 'aa:ac:cd:11:22:33'},
            return_fields=mock.ANY)
        self.assertIsInstance(fixed_addr, objects.FixedAddressV4)
        connector.create_object.assert_called_once_with(
            'fixedaddress',
            {'network_view': 'some-view', 'ipv4addr': '192.168.1.15',
             'mac': 'aa:ac:cd:11:22:33'}, mock.ANY)

    def test_create_fixed_address_v6(self):
        mock_fixed_address = {
            '_ref': 'ipv6fixedaddress/ZG5zLmhvc3QkLl9kZWZhdWx0LmNvbS5nbG9iYA',
            'ipv6addr': 'fffe:1234:1234::1',
            'duid': '00:23:97:49:aa:ac:cd:11:22:33',
        }
        connector = self._mock_connector(create_object=mock_fixed_address)

        fixed_addr = objects.FixedAddress.create(connector,
                                                 ip='fffe:1234:1234::1',
                                                 network_view='some-view',
                                                 mac='aa:ac:cd:11:22:33')
        self.assertIsInstance(fixed_addr, objects.FixedAddressV6)
        self.assertEqual(mock_fixed_address['duid'], fixed_addr.duid)

        connector.get_object.assert_called_once_with(
            'ipv6fixedaddress',
            {'network_view': 'some-view', 'ipv6addr': 'fffe:1234:1234::1',
             'duid': mock.ANY},
            return_fields=mock.ANY)
        connector.create_object.assert_called_once_with(
            'ipv6fixedaddress',
            {'network_view': 'some-view', 'ipv6addr': 'fffe:1234:1234::1',
             'duid': mock.ANY}, mock.ANY)

    @mock.patch('infoblox_client.utils.generate_duid')
    def test_fixed_address_v6(self, generate):
        mac = 'aa:ac:cd:11:22:33'
        duid = '00:0a:d3:9b:aa:ac:cd:11:22:33'
        generate.return_value = duid
        connector = self._mock_connector()
        fixed_addr = objects.FixedAddress(connector,
                                          ip='fffe:1234:1234::1',
                                          network_view='some-view',
                                          mac=mac)
        self.assertIsInstance(fixed_addr, objects.FixedAddressV6)
        self.assertEqual(mac, fixed_addr.mac)
        self.assertEqual(duid, fixed_addr.duid)
        generate.assert_called_once_with(mac)

    def test_search_ipaddress(self):
        ip_mock = [{'_ref': ('ipv4address/Li5pcHY0X2FkZHJlc3MkMTky'
                             'LjE2OC4xLjEwLzE:192.168.1.10/my_view'),
                    'objects': ['ref_1', 'ref_2']}]
        connector = self._mock_connector(get_object=ip_mock)
        ip = objects.IPAddress.search(connector,
                                      network_view='some_view',
                                      ip_address='192.168.1.5')
        payload = {'network_view': 'some_view', 'ip_address': '192.168.1.5'}
        connector.get_object.assert_called_once_with(
            'ipv4address', payload, return_fields=mock.ANY,
            extattrs=None, force_proxy=mock.ANY)
        self.assertIsInstance(ip, objects.IPv4Address)
        self.assertEqual(ip_mock[0]['objects'], ip.objects)

    def test_ea_parse_generate(self):
        eas = {'Subnet ID': {'value': 'some-id'},
               'Tenant Name': {'value': 'tenant-name'},
               'Cloud API Owned': {'value': 'True'},
               'Some EA': {'value': 'False'},
               'Zero EA': {'value': '0'}}
        ea = objects.EA.from_dict(eas)
        self.assertIsInstance(ea, objects.EA)
        # validate True and False are converted to booleans
        self.assertEqual(True, ea.get('Cloud API Owned'))
        self.assertEqual(False, ea.get('Some EA'))
        self.assertEqual('0', ea.get('Zero EA'))
        self.assertEqual(eas, ea.to_dict())

    def test_ea_to_dict(self):
        ea = {'Subnet ID': 'some-id',
              'Tenant Name':  'tenant-name',
              'Cloud API Owned': 'True',
              'DNS Record Types': ['record_a', 'record_ptr'],
              'False String EA': 'False',
              'Empty String EA': '',
              'False EA': False,
              'Zero EA': 0,
              'None EA': None,
              'None String EA': 'None',
              'Empty List EA': [],
              'Zero String EA': '0'}
        ea_exist = ['Subnet ID',
                    'Tenant Name',
                    'Cloud API Owned',
                    'DNS Record Types',
                    'False String EA',
                    'False EA',
                    'Zero EA',
                    'None String EA',
                    'Zero String EA']
        ea_purged = ['Empty String EA',
                     'None EA',
                     'Empty List EA']
        ea_dict = objects.EA(ea).to_dict()
        self.assertIsInstance(ea_dict, dict)
        for key in ea_exist:
            self.assertEqual(True, key in ea_dict)
        for key in ea_purged:
            self.assertEqual(False, key in ea_dict)
        for key in ea_exist:
            self.assertEqual(str(ea.get(key)), ea_dict.get(key).get('value'))

    def test_ea_returns_none(self):
        for ea in (None, '', 0):
            self.assertEqual(None, objects.EA.from_dict(ea))

    def test_ea_set_get(self):
        ea = objects.EA()
        ea_name = 'Subnet ID'
        id = 'subnet-id'
        generated_eas = {ea_name: {'value': id}}
        ea.set(ea_name, id)
        self.assertEqual(id, ea.get(ea_name))
        self.assertEqual(generated_eas, ea.to_dict())
