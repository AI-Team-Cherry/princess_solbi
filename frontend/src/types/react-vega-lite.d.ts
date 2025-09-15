declare module 'react-vega-lite' {
  import * as React from 'react';
  export interface VegaLiteProps {
    spec: object;
    data?: { [key: string]: any };
    [key: string]: any;
  }
  export default class VegaLite extends React.Component<VegaLiteProps> {}
}