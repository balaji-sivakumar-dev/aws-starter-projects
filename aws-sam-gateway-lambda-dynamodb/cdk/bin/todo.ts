//!/usr/bin/env node
import 'source-map-support/register';
import { App } from 'aws-cdk-lib';
import { TodoStack } from '../lib/todo-stack';

const app = new App();
new TodoStack(app, 'TodoCdkStack', {});
