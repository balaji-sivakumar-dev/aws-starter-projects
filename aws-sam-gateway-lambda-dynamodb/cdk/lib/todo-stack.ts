import { Duration, Stack, StackProps, CfnOutput } from 'aws-cdk-lib';
import { Construct } from 'constructs';
import { AttributeType, BillingMode, Table } from 'aws-cdk-lib/aws-dynamodb';
import { Runtime, Code, Function as LambdaFn } from 'aws-cdk-lib/aws-lambda';
import { HttpApi, CorsHttpMethod } from 'aws-cdk-lib/aws-apigatewayv2';
import { LambdaProxyIntegration } from 'aws-cdk-lib/aws-apigatewayv2-integrations';
import * as path from 'path';

export class TodoStack extends Stack {
  constructor(scope: Construct, id: string, props?: StackProps) {
    super(scope, id, props);

    const table = new Table(this, 'TodoTable', {
      billingMode: BillingMode.PAY_PER_REQUEST,
      partitionKey: { name: 'id', type: AttributeType.STRING },
    });

    table.addGlobalSecondaryIndex({
      indexName: 'status-index',
      partitionKey: { name: 'status', type: AttributeType.STRING },
    });

    const fn = new LambdaFn(this, 'TodoFunction', {
      runtime: Runtime.PYTHON_3_11,
      handler: 'app.handler',
      code: Code.fromAsset(path.join(__dirname, '../../src')),
      timeout: Duration.seconds(20),
      environment: {
        TABLE_NAME: table.tableName,
      },
    });

    table.grantReadWriteData(fn);

    const api = new HttpApi(this, 'HttpApi', {
      corsPreflight: {
        allowMethods: [CorsHttpMethod.ANY],
        allowOrigins: ['*'],
        allowHeaders: ['*'],
      },
    });

    api.addRoutes({
      path: '/todos',
      methods: [ 'GET' as any, 'POST' as any ],
      integration: new LambdaProxyIntegration({ handler: fn }),
    });

    api.addRoutes({
      path: '/todos/{id}',
      methods: [ 'GET' as any, 'PUT' as any, 'DELETE' as any ],
      integration: new LambdaProxyIntegration({ handler: fn }),
    });

    new CfnOutput(this, 'ApiUrl', { value: api.apiEndpoint });
    new CfnOutput(this, 'TableName', { value: table.tableName });
  }
}
