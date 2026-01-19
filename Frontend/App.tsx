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
import StageResultScreen from './screens/StageResultsScreen';

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

// Production API URL - FIXED: No process usage
const isDevelopment = __DEV__; // React Native's built-in flag

const API_BASE_URL = !isDevelopment
  ? 'https://your-agritech-backend.azurewebsites.net'  // Your Azure App Service URL
  : 'http://10.67.8.16:3001';  // Local dev (Android)

// Global configuration
(globalThis as any).API_BASE_URL = API_BASE_URL;

export default function App() {
  return (
    <NavigationContainer>
      <Stack.Navigator
        initialRouteName="Login"
        screenOptions={{
          headerShown: false,
        }}>
        <Stack.Screen 
          name="Login" 
          component={LoginScreen} 
          options={{headerTitle: 'Login to Agritech'}}
        />
        <Stack.Screen
          name="Home"
          component={HomeScreen}
          options={{ headerTitle: 'Farm Plot Mapper' }}
        />
        <Stack.Screen 
          name="PlotForm" 
          component={PlotFormScreen} 
        />
        <Stack.Screen
          name="Map"
          component={MapScreen}
          options={{ headerTitle: 'Draw Your Plot' }}
        />
        <Stack.Screen
          name="Results"
          component={ResultsScreen}
          options={{ headerTitle: 'Analysis Results' }} 
        />
        <Stack.Screen 
          name="CropSelection" 
          component={CropSelectionScreen} 
        />
        <Stack.Screen 
          name="StageResult" 
          component={StageResultScreen} 
        />
        <Stack.Screen 
          name="DiseaseResult" 
          component={DiseaseResultScreen} 
        />
        <Stack.Screen 
          name="PestResult" 
          component={PestResultScreen} 
        />
      </Stack.Navigator>
    </NavigationContainer>
  );
}