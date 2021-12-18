import logging

import boto3

LOGGER = logging.getLogger(__name__)
handler = logging.StreamHandler()
formatter = logging.Formatter(fmt='%(asctime)s - %(levelname)s - [%(module)s:%(lineno)d] - %(funcName)s - %(message)s',
                              datefmt='%b-%d-%Y %I:%M:%S %p')
handler.setFormatter(fmt=formatter)
LOGGER.addHandler(hdlr=handler)
LOGGER.setLevel(level=logging.DEBUG)

client = boto3.client('route53')


def get_zone_id(dns: str = None) -> str or None:
    """Gets the zone ID of a DNS name registered in route53.

    Args:
        dns: Takes the hosted zone name.

    Returns:
        str or None:
        Returns the zone ID.
    """
    response = client.list_hosted_zones_by_name(DNSName=dns, MaxItems='1')

    if response.get('ResponseMetadata', {}).get('HTTPStatusCode') != 200:
        LOGGER.error(response)
        return

    if hosted_zones := response.get('HostedZones'):
        if zone_id := hosted_zones[0].get('Id'):
            return zone_id.split('/')[-1]
    else:
        LOGGER.error(f'No HostedZones found for the DNSName: {dns}\n{response}')
        return


def add_record_set(dns_name: str, source: str, destination: str, record_type: str) -> dict or None:
    """Adds a record set under an existing hosted zone.

    Args:
        dns_name: Zone name.
        source: Source DNS name. Can be either ``subdomain.domain.com`` or just the ``subdomain``.
        destination: Destination hostnames or IP addresses.
        record_type: Type of the record to be added.

    Returns:
        dict or None:
        ChangeSet response from AWS.
    """
    supported_records = ['SOA', 'A', 'TXT', 'NS', 'CNAME', 'MX', 'NAPTR', 'PTR', 'SRV', 'SPF', 'AAAA', 'CAA', 'DS']
    if record_type not in supported_records:
        LOGGER.error('Unsupported record type passed.')
        LOGGER.warning(f"Should be one of {', '.join(sorted(supported_records))}")
        return
    if not source.endswith(dns_name):
        source = f'{source}.{dns_name}'
    response = client.change_resource_record_sets(
        HostedZoneId=get_zone_id(dns=dns_name),
        ChangeBatch={
            'Comment': f'{record_type}: {source} -> {destination}',
            'Changes': [
                {
                    'Action': 'UPSERT',
                    'ResourceRecordSet': {
                        'Name': source,
                        'Type': record_type,
                        'TTL': 300,
                        'ResourceRecords': [{'Value': destination}],
                    }
                },
            ]
        }
    )
    if response.get('ResponseMetadata', {}).get('HTTPStatusCode') != 200:
        LOGGER.error(response)
        return
    LOGGER.info(response.get('ChangeInfo', {}).get('Comment'))
    return response.get('ChangeInfo')
