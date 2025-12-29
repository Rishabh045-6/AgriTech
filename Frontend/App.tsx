// App.tsx
import React from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import HomeScreen from './screens/HomeScreen';
import LoginScreen from './screens/LoginScreen';
import MapScreen from './screens/MapScreen';
import ResultsScreen from './screens/ResultsScreen';
import PlotFormScreen from './screens/PlotformScreen';
import CropSelectionScreen from './screens/CropSelectionScreen';
import DiseaseResultScreen from './screens/DiseaseResultScreen';
import PestResultScreen from './screens/PestResultScreen';
import StageResultsScreen from './screens/StageResultsScreen';

export type RootStackParamList = {
  Login: undefined;
  Home: undefined;
  Map: undefined;
  Results: undefined;
  CropSelection: undefined;
  PlotForm: undefined;
  DiseaseResult: undefined;
  PestResult: undefined;
  StageResult: undefined;

};

const Stack = createNativeStackNavigator<RootStackParamList>();

export default function App() {
  return (
    <NavigationContainer>
      <Stack.Navigator
        initialRouteName="Login"
        screenOptions={{
          headerShown: false,
          }}>
          <Stack.Screen name="Login" component={LoginScreen} 
          options={{headerTitle: 'Login to Agritech'}}/>
        <Stack.Screen
          name="Home"
          component={HomeScreen}
          options={{ headerTitle: 'Farm Plot Mapper' }}
        />
        <Stack.Screen name="PlotForm" component={PlotFormScreen} />
        <Stack.Screen
          name="Map"
          component={MapScreen}
          options={{ headerTitle: 'Draw Your Plot' }}
        />
        <Stack.Screen
          name="Results"
          component={ResultsScreen}
          options={{ headerTitle: 'Analysis Results' }} />
        <Stack.Screen name="CropSelection" component={CropSelectionScreen} />
        <Stack.Screen name="StageResult" component={StageResultsScreen} />
        <Stack.Screen name="DiseaseResult" component={DiseaseResultScreen} />
        <Stack.Screen name="PestResult" component={PestResultScreen} />
      </Stack.Navigator>
    </NavigationContainer>
  );
}