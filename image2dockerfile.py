#!venv/bin/python
# -*- encoding: utf-8 -*-
import json
import base64
import requests
import time
import os

class Portainer(object):
    host = None
    username = None
    password = None
    _token = None
    exp_time = None

    def __init__(self, host, username, password):
        self.host = host
        self.username = username
        self.password = password

    @property
    def token(self):
        if self._token is None or (time.time() > self.exp_time + 10):
            self.get_token()
        return self._token
    
    def get_token(self):
        response = requests.post(self.host.rstrip('/')+'/api/auth', json={'username': self.username, 'password': self.password})
        response_json = response.json()

        self._token = response_json.get('jwt')
        self.exp_time = json.loads(base64.b64decode(self._token.split('.')[1]).decode('utf-8'))['exp']

    def get_endpoints(self, limit=1000):
        uri = '/api/endpoints?start=1&limit={}'
        headers={'Authorization': 'Bearer ' + self.token}
        return requests.get(self.host.rstrip('/')+uri.format(limit), headers=headers).json()
    
    def get_images_by_ep_id(self, ep_id):
        uri = '/api/endpoints/{}/docker/images/json?all=1'.format(ep_id)
        headers={'Authorization': 'Bearer ' + self.token}
        data = requests.get(self.host.rstrip('/')+uri, headers=headers).json()
        return data
    
    def get_containers_by_ep_id(self, ep_id):
        uri = '/api/endpoints/{}/docker/containers/json?all=1'.format(ep_id)
        headers={'Authorization': 'Bearer ' + self.token}
        return requests.get(self.host.rstrip('/')+uri, headers=headers).json()
    
    def get_images(self, ep_id, only_using=False):
        data = []
        if only_using:
            for c in self.get_containers_by_ep_id(ep_id):
                if c['Image'] != c["ImageID"]:
                    data.append(c['Image'])
                else:
                    print('{} container`s image has no tag'.format(c))
            return data
        images = self.get_images_by_ep_id(ep_id)
        for image in images:
            if image['RepoTags']:
                data.append(image['RepoTags'][0])
        return data
        
    def get_all_images(self, only_using=False, replace2latest=False, ignore_prefixes=None):
        images = []
        for endpoint in self.get_endpoints():
            if endpoint['Status'] == 1:
                images += (self.get_images(endpoint['Id'], only_using=only_using) or [])
        new_images = []
        if not replace2latest:
            new_images = images
        else:
            for image in images:
                new_images.append(image.split(':')[0]+':'+'latest')
        new_images = list(set(new_images))
        if not ignore_prefixes:
            return new_images
        nn_images = []
        for ig_pre in ignore_prefixes or []:
            for ig in new_images:
                if ig.split('/')[0] != ig_pre:
                    nn_images.append(ig)
        return nn_images

import os

# 使用environ方法
PORTAINER_HOST = os.environ['PORTAINER_HOST']
PORTAINER_USERNAME = os.environ['PORTAINER_USERNAME']
PORTAINER_PASSWORD = os.environ['PORTAINER_PASSWORD']


pcli = Portainer(host=PORTAINER_HOST, username=PORTAINER_USERNAME, password=PORTAINER_PASSWORD)
images = pcli.get_all_images(only_using=True, replace2latest=True, ignore_prefixes=['registry.cn-hangzhou.aliyuncs.com'])
for image in images:
    file_name = image.split(':')[0].replace('/','__').replace('.', '_')
    content = 'FROM {}'.format(image)
    with open('Dockerfiles/Dockerfile-{}'.format(file_name), 'w') as f:
        f.write(content)
        print('write {} to {}'.format(content, file_name))
        