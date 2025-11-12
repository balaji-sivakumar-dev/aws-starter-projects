import { Duration, Stack, StackProps, CfnOutput } from 'aws-cdk-lib';
import { Construct } from 'constructs';
import { AttributeType, BillingMode, Table } from 'aws-cdk-lib/aws-dynamodb';
import { Runtime } from 'aws-cdk-lib/aws-lambda';
import { PythonFunction } from '@aws-cdk/aws-lambda-python-alpha';
import { RestApi, LambdaIntegration, Cors } from 'aws-cdk-lib/aws-apigateway';
import * as path from 'path';

export class TodoStack extends Stack {
  constructor(scope: Construct, id: string, props?: StackProps) {
    super(scope, id, props);

    const table = new Table(this, 'TodoTable', {
      billingMode: BillingMode.PAY_PER_REQUEST,
      partitionKey: { name: 'id', type: AttributeType.STRING },
      tableName: `${this.stackName}-todos`,
    });

    table.addGlobalSecondaryIndex({
      indexName: 'status-index',
      partitionKey: { name: 'status', type: AttributeType.STRING },
    });

    const fn = new PythonFunction(this, 'TodoFunction', {
      runtime: Runtime.PYTHON_3_13,
      entry: path.join(__dirname, '../../src'),
      index: 'app.py',
      handler: 'handler',
      timeout: Duration.seconds(20),
      environment: {
        TABLE_NAME: table.tableName,
      },
    });

    table.grantReadWriteData(fn);

    const api = new RestApi(this, 'TodoApi', {
      deployOptions: { stageName: 'v1' },
      defaultCorsPreflightOptions: {
        allowOrigins: Cors.ALL_ORIGINS,
        allowMethods: Cors.ALL_METHODS,
        allowHeaders: Cors.DEFAULT_HEADERS,
      },
    });

    const todos = api.root.addResource('todos');
    const todosById = todos.addResource('{id}');

    const lambdaIntegration = new LambdaIntegration(fn);
    todos.addMethod('GET', lambdaIntegration);
    todos.addMethod('POST', lambdaIntegration);
    todosById.addMethod('GET', lambdaIntegration);
    todosById.addMethod('PUT', lambdaIntegration);
    todosById.addMethod('DELETE', lambdaIntegration);

    new CfnOutput(this, 'ApiUrl', { value: api.url ?? '' });
    new CfnOutput(this, 'TableName', { value: table.tableName });
  }
}
